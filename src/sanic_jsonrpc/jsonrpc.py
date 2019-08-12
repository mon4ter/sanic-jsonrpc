from collections import namedtuple
from logging import getLogger
from typing import Callable, Dict, Optional, Tuple

from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from sanic.websocket import WebSocketCommonProtocol

__all__ = [
    'logger',
    'Jsonrpc',
]

Annotations = Dict[str, type]
Route = namedtuple('Method', ('name', 'func', 'params', 'result'))
logger = getLogger(__name__)


class Jsonrpc:
    async def _post(self, request: SanicRequest) -> HTTPResponse:
        response = ...(self, request)
        content_type = 'application/json' if response else 'text/plain'
        return HTTPResponse(response, 207, content_type=content_type)

    async def _ws(self, request: SanicRequest, ws: WebSocketCommonProtocol):
        ...

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

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None):
        self.app = app

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        self._post_routes = {}
        self._ws_routes = {}

    def __call__(self, name: Optional[str] = None, *, post_: bool = True, ws_: bool = True, **annotations) -> Callable:
        if isinstance(name, Callable):
            return self.__call__(name.__name__, post_=post_, ws_=ws_)(name)

        def deco(func: Callable) -> Callable:
            if name:
                func.__name__ = name

            route = Route(
                name or func.__name__,
                func,
                *self._annotations(getattr(func, '__annotations__', {}), annotations)
            )

            if post_:
                self._post_routes[route.name] = route

            if ws_:
                self._ws_routes[route.name] = route

            return func

        return deco

    def post(self, name: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name, post_=True, ws_=False, **annotations)

    def ws(self, name: Optional[str] = None, **annotations) -> Callable:
        return self.__call__(name, post_=False, ws_=True, **annotations)

    def method(self, name: Optional[str] = None, *, post_: bool = True, ws_: bool = True, **annotations) -> Callable:
        return self.__call__(name, post_=post_, ws_=ws_, **annotations)
