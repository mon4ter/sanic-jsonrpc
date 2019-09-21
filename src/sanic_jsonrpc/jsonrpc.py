from asyncio import CancelledError, FIRST_COMPLETED, Future, Queue, ensure_future, gather, iscoroutine, shield, wait
from collections import namedtuple
from functools import partial
from logging import getLogger
from typing import Any, AnyStr, Callable, Dict, List, Optional, Tuple, Union

from fashionable import ModelAttributeError, ModelError, UNSET, validate
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from sanic.websocket import WebSocketCommonProtocol
from ujson import dumps, loads

from .errors import INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, PARSE_ERROR
from .models import Error, Notification, Request, Response

__all__ = [
    'logger',
    'Jsonrpc',
    'Notifier',
]

_Annotations = Dict[str, type]
_Incoming = Union[Request, Notification]
_Outgoing = Union[Response, Notification]
_JsonrpcType = Union[_Incoming, _Outgoing]
_Route = namedtuple('Route', ('name', 'func', 'params', 'result'))
_response = partial(Response, '2.0')

Notifier = Callable[[Notification], None]
logger = getLogger(__name__)


class Jsonrpc:
    @staticmethod
    def _annotations(annotations: _Annotations, extra: _Annotations) -> Tuple[Optional[_Annotations], Optional[type]]:
        result = annotations.pop('return', None)
        result = extra.pop('result', result)
        annotations.update(extra)
        return annotations or None, result

    def _route(self, incoming: _Incoming, is_post: bool) -> Optional[Union[_Route, Response]]:
        is_request = isinstance(incoming, Request)
        route = self._routes.get((is_post, is_request, incoming.method))

        if route:
            return route

        if is_request:
            return _response(error=METHOD_NOT_FOUND, id=incoming.id)

    @staticmethod
    def _parse_json(json: AnyStr) -> Union[Dict, List[Dict], Response]:
        try:
            return loads(json)
        except (TypeError, ValueError):
            return _response(error=PARSE_ERROR)

    @staticmethod
    def _parse_message(message: Dict) -> _JsonrpcType:
        try:
            return Request(**message)
        except (TypeError, ModelError) as err:
            if isinstance(err, ModelAttributeError) and err.kwargs['attr'] == 'id':
                return Notification(**message)

            return _response(error=INVALID_REQUEST)

    def _parse_messages(self, request: SanicRequest) -> Union[_JsonrpcType, List[_JsonrpcType]]:
        messages = self._parse_json(request.body)

        if isinstance(messages, Response):
            return messages

        if isinstance(messages, list):
            if not messages:
                return _response(error=INVALID_REQUEST)

            return [self._parse_message(m) for m in messages]

        return self._parse_message(messages)

    def _serialize(self, obj: Any) -> str:
        try:
            return dumps(obj)
        except (TypeError, ValueError) as err:
            # TODO test unserializable response
            logger.error("Failed to serialize object %r: %s", obj, err, exc_info=err)
            return self._serialize(_response(error=INTERNAL_ERROR))

    def _serialize_responses(self, responses: List[Response], single: bool) -> Optional[str]:
        if not responses:
            return None

        if single:
            return self._serialize(dict(responses[0]))

        return self._serialize([dict(r) for r in responses])

    def _register_call(self, *args, **kwargs) -> Future:
        fut = shield(self._call(*args, **kwargs))
        self._calls.put_nowait(fut)
        return fut

    async def _call(
            self,
            incoming: _Incoming,
            route: _Route,
            sanic_request: SanicRequest,
            ws: Optional[WebSocketCommonProtocol] = None
    ) -> Optional[Response]:
        logger.debug("--> %r", incoming)

        args = []
        kwargs = {}

        # TODO validate params
        if isinstance(incoming.params, dict):
            kwargs.update(incoming.params)
        elif isinstance(incoming.params, list):
            args.extend(incoming.params)

        if route.params:
            for name, typ in route.params.items():
                if typ is SanicRequest:
                    kwargs[name] = sanic_request
                elif typ is WebSocketCommonProtocol:
                    kwargs[name] = ws
                elif typ is Sanic:
                    kwargs[name] = self.app
                elif typ is Request or typ is Notification:
                    # TODO test notification
                    kwargs[name] = incoming
                elif typ is Notifier:
                    kwargs[name] = self._notifier(ws) if ws else None

        result = UNSET
        error = UNSET

        try:
            ret = route.func(*args, **kwargs)

            if iscoroutine(ret):
                ret = await ret
        except Error as err:
            error = err
        except TypeError:
            error = INVALID_PARAMS
        except Exception as err:
            logger.error("%r failed: %s", incoming, err, exc_info=err)
            error = INTERNAL_ERROR
        else:
            if isinstance(ret, Error):
                error = ret
            elif route.result:
                try:
                    result = validate(route.result, ret, strict=False)
                except (TypeError, ValueError) as err:
                    logger.error("Invalid response to %r: %s", incoming, err, exc_info=err)
                    error = INTERNAL_ERROR
            else:
                result = ret

        if isinstance(incoming, Request):
            response = Response('2.0', result=result, error=error, id=incoming.id)
            logger.debug("<-- %r", response)
            return response

    async def _post(self, sanic_request: SanicRequest) -> HTTPResponse:
        incomings = self._parse_messages(sanic_request)

        single = not isinstance(incomings, list)

        if single:
            incomings = [incomings]

        responses = []
        futures = []

        for incoming in incomings:
            if isinstance(incoming, Response):
                responses.append(incoming)
                continue

            route = self._route(incoming, is_post=True)

            if not isinstance(route, _Route):
                if route:
                    responses.append(route)
                else:
                    logger.info("Unhandled %r", incoming)

                continue

            fut = self._register_call(incoming, route, sanic_request)

            if isinstance(incoming, Request):
                futures.append(fut)

        for response in await gather(*futures):
            responses.append(response)

        body = self._serialize_responses(responses, single)
        content_type = 'application/json' if body else 'text/plain'
        return HTTPResponse(body, 207, content_type=content_type)

    def _ws_outgoing(self, ws: WebSocketCommonProtocol, outgoing: _Outgoing) -> Future:
        return ensure_future(ws.send(self._serialize(dict(outgoing))))

    async def _ws(self, sanic_request: SanicRequest, ws: WebSocketCommonProtocol):
        recv = None
        pending = set()

        while True:
            if recv not in pending:
                recv = ensure_future(ws.recv())

                pending.add(recv)

            done, pending = await wait(pending, return_when=FIRST_COMPLETED)

            for fut in done:
                err = fut.exception()

                if err:
                    # TODO test exception in call
                    logger.error("%s", err, exc_info=err)
                    continue

                result = fut.result()

                if not result:
                    continue

                if isinstance(result, Response):
                    pending.add(self._ws_outgoing(ws, result))
                    continue

                obj = self._parse_json(result)

                if isinstance(obj, Response):
                    pending.add(self._ws_outgoing(ws, obj))
                    continue

                incoming = self._parse_message(obj)

                if isinstance(incoming, Response):
                    pending.add(self._ws_outgoing(ws, incoming))
                    continue

                route = self._route(incoming, is_post=False)

                if not isinstance(route, _Route):
                    if route:
                        pending.add(self._ws_outgoing(ws, route))
                    else:
                        logger.info("Unhandled %r", incoming)

                    continue

                fut = self._register_call(incoming, route, sanic_request, ws)

                if isinstance(incoming, Request):
                    pending.add(fut)

    async def _processing(self):
        calls = self._calls

        try:
            while True:
                call = await calls.get()
                await call
        except CancelledError:
            pass
        finally:
            while not calls.empty():
                # TODO test stop Sanic while call is processing
                await calls.get_nowait()

    def _notifier(self, ws) -> Notifier:
        def notifier(notification: Notification):
            # TODO test outgoing notifications
            # TODO save futures
            self._ws_outgoing(ws, notification)
        return notifier

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None):
        self.app = app

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        self._routes = {}
        self._calls = Queue()
        self._processing_task = None

        @app.listener('after_server_start')
        async def start_processing(_app, _loop):
            self._processing_task = ensure_future(self._processing())

        @app.listener('before_server_stop')
        async def finish_calls(_app, _loop):
            self._processing_task.cancel()
            await self._processing_task

    def __call__(
            self,
            name_: Optional[str] = None,
            *,
            is_post_: Optional[bool] = None,
            is_request_: Optional[bool] = None,
            **annotations
    ) -> Callable:
        if isinstance(name_, Callable):
            return self.__call__(is_post_=is_post_, is_request_=is_request_)(name_)

        def deco(func: Callable) -> Callable:
            if name_:
                func.__name__ = name_

            route = _Route(
                name_ or func.__name__,
                func,
                *self._annotations(getattr(func, '__annotations__', {}), annotations)
            )

            if is_post_ is None and is_request_ is None:
                self._routes[True, True, route.name] = route
                self._routes[True, False, route.name] = route
                self._routes[False, True, route.name] = route
                self._routes[False, False, route.name] = route
            elif is_post_ is None:
                self._routes[True, is_request_, route.name] = route
                self._routes[False, is_request_, route.name] = route
            elif is_request_ is None:
                self._routes[is_post_, True, route.name] = route
                self._routes[is_post_, False, route.name] = route
            else:
                self._routes[is_post_, is_request_, route.name] = route

            return func

        return deco

    def post(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=True, **annotations)

    def ws(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=False, **annotations)

    def request(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_request_=True, **annotations)

    def notification(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_request_=False, **annotations)

    def post_request(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=True, is_request_=True, **annotations)

    def ws_request(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=False, is_request_=True, **annotations)

    def post_notification(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=True, is_request_=False, **annotations)

    def ws_notification(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, is_post_=False, is_request_=False, **annotations)
