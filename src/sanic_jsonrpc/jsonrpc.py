from asyncio import gather, get_event_loop, iscoroutine, Queue
from collections import namedtuple
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from fashionable import ModelAttributeError, ModelError
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from sanic.websocket import WebSocketCommonProtocol
from ujson import dumps, loads

from .models import Notification, Request, Response, Error

__all__ = [
    'logger',
    'Jsonrpc',
]

Annotations = Dict[str, type]
Message = Union[Request, Notification]
JsonrpcType = Union[Message, Response]
Route = namedtuple('Method', ('name', 'func', 'params', 'result'))
logger = getLogger(__name__)


class Jsonrpc:
    @staticmethod
    def _annotations(annotations: Annotations, extra: Annotations) -> Tuple[Optional[Annotations], Optional[type]]:
        result = annotations.pop('return', None)
        result = extra.pop('result', result)
        annotations.update(extra)
        return annotations or None, result

    def _route_post(self, method: str) -> Optional[Route]:
        return self._post_routes.get(method)

    def _route_ws(self, method: str) -> Optional[Route]:
        return self._ws_routes.get(method)

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

            return Response('2.0', error=(-32600, "Invalid Request"))

    def _parse_messages(self, request: SanicRequest) -> Union[JsonrpcType, List[JsonrpcType]]:
        try:
            messages = loads(request.body)
        except (TypeError, ValueError):
            return Response('2.0', error=(-32700, "Parse error"))

        if isinstance(messages, list):
            if not messages:
                return Response('2.0', error=(-32600, "Invalid Request"))
            else:
                return [self._parse_message(m) for m in messages]
        else:
            return self._parse_message(messages)

    def _serialize(self, obj: Any) -> str:
        try:
            return dumps(obj)
        except (TypeError, ValueError) as err:
            logger.error("Failed to serialize response: %s", err)
            return self._serialize_responses([Response('2.0', error=(-32603, "Internal error"))], single=True)

    def _serialize_responses(self, responses: List[Response], single: bool) -> Optional[str]:
        if not responses:
            return None

        if single:
            return self._serialize(self.response(responses[0]))

        return self._serialize([self.response(r) for r in responses])

    async def _call(self, message: Message, route: Route, sanic_request: SanicRequest) -> Optional[Response]:
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
                    continue
                elif typ is Sanic:
                    kwargs[name] = self.app
                    continue

        try:
            result = route.func(*args, **kwargs)

            if iscoroutine(result):
                result = await result
        except Error as error:
            response = Response('2.0', error=error)
        except TypeError:
            response = Response('2.0', error=(-32602, "Invalid params"))
        except Exception as err:
            logger.error("%r failed: %s", message, err, exc_info=err)
            response = Response('2.0', error=(-32603, "Internal error"))
        else:
            # TODO validate result
            response = Response('2.0', result=result)

        if isinstance(message, Request):
            response.id = message.id
            logger.debug("<-- %r", response)
            return response

    async def _post(self, sanic_request: SanicRequest) -> HTTPResponse:
        messages = self._parse_messages(sanic_request)

        single = not isinstance(messages, list)

        if single:
            messages = [messages]

        responses = []
        tasks = []

        for message in messages:
            if isinstance(message, Response):
                responses.append(message)
                continue

            route = self._route_post(message.method)

            if not route:
                if isinstance(message, Request):
                    responses.append(Response('2.0', error=(-32601, "Method not found"), id=message.id))
                else:
                    logger.info("Unhandled %r", message)

                continue

            task = get_event_loop().create_task(self._call(message, route, sanic_request))
            self._calls.put_nowait(task)

            if isinstance(message, Request):
                tasks.append(task)

        for response in await gather(*tasks):
            responses.append(response)

        body = self._serialize_responses(responses, single)
        content_type = 'application/json' if body else 'text/plain'
        return HTTPResponse(body, 207, content_type=content_type)

    async def _ws(self, request: SanicRequest, ws: WebSocketCommonProtocol):
        ...

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None):
        self.app = app

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        self._post_routes = {}
        self._ws_routes = {}
        self._calls = Queue()

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
