from asyncio import CancelledError, FIRST_COMPLETED, Future, Queue, ensure_future, gather, iscoroutine, shield, wait
from collections import namedtuple
from logging import getLogger
from typing import Any, AnyStr, Callable, Dict, List, Optional, Tuple, Union

from fashionable import ModelAttributeError, ModelError
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
]

Annotations = Dict[str, type]
Message = Union[Request, Notification]
JsonrpcType = Union[Message, Response]
Route = namedtuple('Route', ('name', 'func', 'params', 'result'))
logger = getLogger(__name__)


class Jsonrpc:
    @staticmethod
    def _annotations(annotations: Annotations, extra: Annotations) -> Tuple[Optional[Annotations], Optional[type]]:
        result = annotations.pop('return', None)
        result = extra.pop('result', result)
        annotations.update(extra)
        return annotations or None, result

    @staticmethod
    def _route(message: Message, routes: Dict[str, Route]) -> Optional[Union[Route, Response]]:
        route = routes.get(message.method)

        if route:
            return route

        if isinstance(message, Request):
            return Response('2.0', error=METHOD_NOT_FOUND, id=message.id)

    def _route_post(self, message: Message) -> Optional[Union[Route, Response]]:
        return self._route(message, self._post_routes)

    def _route_ws(self, message: Message) -> Optional[Union[Route, Response]]:
        return self._route(message, self._ws_routes)

    @staticmethod
    def _parse_json(json: AnyStr) -> Union[Dict, List[Dict], Response]:
        try:
            return loads(json)
        except (TypeError, ValueError):
            return Response('2.0', error=PARSE_ERROR)

    @staticmethod
    def _parse_message(message: Dict) -> JsonrpcType:
        try:
            return Request(**message)
        except (TypeError, ModelError) as err:
            if isinstance(err, ModelAttributeError) and err.kwargs['attr'] == 'id':
                try:
                    return Notification(**message)
                except (TypeError, ModelError):
                    pass

            return Response('2.0', error=INVALID_REQUEST)

    def _parse_messages(self, request: SanicRequest) -> Union[JsonrpcType, List[JsonrpcType]]:
        messages = self._parse_json(request.body)

        if isinstance(messages, Response):
            return messages

        if isinstance(messages, list):
            if not messages:
                return Response('2.0', error=INVALID_REQUEST)

            return [self._parse_message(m) for m in messages]

        return self._parse_message(messages)

    def _serialize(self, obj: Any) -> str:
        try:
            return dumps(obj)
        except (TypeError, ValueError) as err:
            logger.error("Failed to serialize object %r: %s", obj, err, exc_info=err)
            return self._serialize_response(Response('2.0', error=INTERNAL_ERROR))

    def _serialize_response(self, response: Response) -> str:
        return self._serialize(self.response(response))

    def _serialize_responses(self, responses: List[Response], single: bool) -> Optional[str]:
        if not responses:
            return None

        if single:
            return self._serialize(self.response(responses[0]))

        return self._serialize([self.response(r) for r in responses])

    def _register_call(self, *args, **kwargs) -> Future:
        fut = shield(self._call(*args, **kwargs))
        self._calls.put_nowait(fut)
        return fut

    async def _call(
            self,
            message: Message,
            route: Route,
            sanic_request: SanicRequest,
            ws: Optional[WebSocketCommonProtocol] = None
    ) -> Optional[Response]:
        logger.debug("--> %r", message)

        args = []
        kwargs = {}

        # TODO validate params
        if isinstance(message.params, dict):
            kwargs.update(message.params)
        elif isinstance(message.params, list):
            args.extend(message.params)

        if route.params:
            for name, typ in route.params.items():
                if typ is SanicRequest:
                    kwargs[name] = sanic_request
                elif typ is WebSocketCommonProtocol:
                    kwargs[name] = ws
                elif typ is Sanic:
                    kwargs[name] = self.app
                elif typ is Request or typ is Notification:
                    kwargs[name] = message

        result = None
        error = None

        try:
            ret = route.func(*args, **kwargs)

            if iscoroutine(ret):
                ret = await ret
        except Error as err:
            error = err
        except TypeError:
            error = INVALID_PARAMS
        except Exception as err:
            logger.error("%r failed: %s", message, err, exc_info=err)
            error = INTERNAL_ERROR
        else:
            # TODO validate result
            result = ret

        if isinstance(message, Request):
            response = Response('2.0', result=result, error=error, id=message.id)
            logger.debug("<-- %r", response)
            return response

    async def _post(self, sanic_request: SanicRequest) -> HTTPResponse:
        messages = self._parse_messages(sanic_request)

        single = not isinstance(messages, list)

        if single:
            messages = [messages]

        responses = []
        futures = []

        for message in messages:
            if isinstance(message, Response):
                responses.append(message)
                continue

            route = self._route_post(message)

            if not isinstance(route, Route):
                if route:
                    responses.append(route)
                else:
                    logger.info("Unhandled %r", message)

                continue

            fut = self._register_call(message, route, sanic_request)

            if isinstance(message, Request):
                futures.append(fut)

        for response in await gather(*futures):
            responses.append(response)

        body = self._serialize_responses(responses, single)
        content_type = 'application/json' if body else 'text/plain'
        return HTTPResponse(body, 207, content_type=content_type)

    def _ws_response(self, ws: WebSocketCommonProtocol, response: Response) -> Future:
        return ensure_future(ws.send(self._serialize_response(response)))

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
                    logger.error("%s", err, exc_info=err)
                    continue

                result = fut.result()

                if not result:
                    continue

                if isinstance(result, Response):
                    pending.add(self._ws_response(ws, result))
                    continue

                obj = self._parse_json(result)

                if isinstance(obj, Response):
                    pending.add(self._ws_response(ws, obj))
                    continue

                message = self._parse_message(obj)

                if isinstance(message, Response):
                    pending.add(self._ws_response(ws, message))
                    continue

                route = self._route_ws(message)

                if not isinstance(route, Route):
                    if route:
                        pending.add(self._ws_response(ws, route))
                    else:
                        logger.info("Unhandled %r", message)

                    continue

                fut = self._register_call(message, route, sanic_request, ws)

                if isinstance(message, Request):
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
                await calls.get_nowait()

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None):
        self.app = app

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        self._post_routes = {}
        self._ws_routes = {}
        self._calls = Queue()
        self._processing_task = None

        @app.listener('after_server_start')
        async def start_processing(_app, _loop):
            self._processing_task = ensure_future(self._processing())

        @app.listener('before_server_stop')
        async def finish_calls(_app, _loop):
            self._processing_task.cancel()
            await self._processing_task

    def __call__(self, name_: Optional[str] = None, *, post_: bool = True, ws_: bool = True, **annotations) -> Callable:
        if isinstance(name_, Callable):
            return self.__call__(name_.__name__, post_=post_, ws_=ws_)(name_)

        def deco(func: Callable) -> Callable:
            if name_:
                func.__name__ = name_

            route = Route(
                name_ or func.__name__,
                func,
                *self._annotations(getattr(func, '__annotations__', {}), annotations)
            )

            if post_:
                self._post_routes[route.name] = route

            if ws_:
                self._ws_routes[route.name] = route

            return func

        return deco

    def post(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, post_=True, ws_=False, **annotations)

    def ws(self, name_: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name_, post_=False, ws_=True, **annotations)

    def method(self, name_: Optional[str] = None, *, post_: bool = True, ws_: bool = True, **annotations) -> Callable:
        return self.__call__(name_, post_=post_, ws_=ws_, **annotations)

    @staticmethod
    def response(response: Response) -> dict:
        obj = dict(response)
        obj.setdefault('id', None)
        return obj
