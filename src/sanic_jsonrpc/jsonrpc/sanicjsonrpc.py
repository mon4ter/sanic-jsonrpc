from asyncio import Future, gather, ensure_future, wait, CancelledError, FIRST_COMPLETED
from typing import Optional, Dict, Any

from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from websockets import WebSocketCommonProtocol as WebSocket

from ._basejsonrpc import BaseJsonrpc
from .._routing import Route
from ..loggers import logger, traffic_logger
from ..models import Notification, Response, Request
from ..notifier import Notifier
from ..types import Outgoing, Incoming

__all__ = [
    'Jsonrpc',
    'SanicJsonrpc',
]


# TODO middleware
class SanicJsonrpc(BaseJsonrpc):
    def _customs(
            self,
            sanic_request: SanicRequest,
            incoming: Incoming,
            ws: Optional[WebSocket] = None,
            notifier: Optional[Notifier] = None
    ) -> Dict[type, Any]:
        return {
            SanicRequest: sanic_request,
            WebSocket: ws,
            Sanic: self.app,
            Request: incoming,
            Notification: incoming,
            Incoming: incoming,
            Notifier: notifier,
        }

    async def _post(self, sanic_request: SanicRequest) -> HTTPResponse:
        incomings = self._parse_messages(sanic_request.body)

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

            if not isinstance(route, Route):
                if route:
                    responses.append(route)
                else:
                    logger.info("Unhandled %r", incoming)

                continue

            fut = self._register_call(incoming, route, self._customs(sanic_request, incoming))

            if isinstance(incoming, Request):
                futures.append(fut)

        for response in await gather(*futures):
            responses.append(response)

        body = self._serialize_responses(responses, single)
        content_type = 'application/json' if body else 'text/plain'
        return HTTPResponse(body, 207, content_type=content_type)

    def _ws_outgoing(self, ws: WebSocket, outgoing: Outgoing) -> Future:
        traffic_logger.debug("<-- %r", outgoing)
        return ensure_future(ws.send(self._serialize(dict(outgoing))))

    async def _ws(self, sanic_request: SanicRequest, ws: WebSocket):
        recv = None
        pending = set()
        notifier = Notifier(ws, self._ws_outgoing, self._finalise_future)

        while ws.open:
            if recv not in pending:
                recv = ensure_future(ws.recv())
                pending.add(recv)

            try:
                done, pending = await wait(pending, return_when=FIRST_COMPLETED)
            except CancelledError:
                for fut in pending:
                    self._finalise_future(fut)

                break

            for fut in done:
                result = self._finalise_future(fut)

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

                if not isinstance(route, Route):
                    if route:
                        pending.add(self._ws_outgoing(ws, route))
                    else:
                        logger.info("Unhandled %r", incoming)

                    continue

                fut = self._register_call(incoming, route, self._customs(sanic_request, incoming, ws, notifier))

                if isinstance(incoming, Request):
                    pending.add(fut)

        notifier.cancel()

        for fut in pending:
            fut.cancel()

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._processing_task = None
        app.listener('after_server_start')(self._start_processing)
        app.listener('before_server_stop')(self._stop_processing)

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)


class Jsonrpc(SanicJsonrpc):
    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn(
            "Class {} has been renamed to {}".format(self.__class__.__name__, self.__class__.__base__.__name__),
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
