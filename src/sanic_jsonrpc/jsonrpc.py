from collections import namedtuple
from functools import partial
from logging import getLogger
from typing import Optional, Callable, Tuple, Union, Dict, FrozenSet

from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from sanic.websocket import WebSocketCommonProtocol

logger = getLogger(__name__)

__all__ = [
    'logger',
    'Jsonrpc',

]

Types = Union[type, Tuple[type, ...]]
Route = namedtuple('Method', ('name', 'func', 'params', 'result'))


class Jsonrpc:
    async def _post(self, request: SanicRequest) -> HTTPResponse:
        response = ...(self, request)
        content_type = 'application/json' if response else 'text/plain'
        return HTTPResponse(response, 207, content_type=content_type)

    async def _ws(self, request: SanicRequest, ws: WebSocketCommonProtocol):
        ...

    @staticmethod
    def _parse_types(
            func: Callable,
            params: Optional[Types] = None,
            result: Optional[type] = None
    ) -> Tuple[Optional[Dict[Union[str, int], type]], Optional[type]]:
        annotations = getattr(func, '__annotations__', {})
        result = result or annotations.get('return')

        if params is not None:
            params = {i: p for i, p in enumerate(params if isinstance(params, tuple) else (params,))}
        else:
            params = {k: v for k, v in annotations.items() if k != 'return'}

        return params or None, result or None

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

    def method(
            self,
            name: Union[Callable, Optional[str]] = None,
            params: Optional[Types] = None,
            result: Optional[type] = None,
            *,
            routes: FrozenSet = frozenset({'post', 'ws'})
    ) -> Callable:
        if isinstance(name, Callable):
            return self.method(name.__name__, routes=routes)(name)

        def deco(func: Callable) -> Callable:
            if name:
                func.__name__ = name

            method = Route(name or func.__name__, func, *self._parse_types(func, params, result))

            if 'post' in routes:
                self._post_routes[method.name] = method

            if 'ws' in routes:
                self._ws_routes[method.name] = method

            return func

        return deco

    rest = partial(method, routes=frozenset({'rest'}))
    ws = partial(method, routes=frozenset({'ws'}))
    __call__ = method
