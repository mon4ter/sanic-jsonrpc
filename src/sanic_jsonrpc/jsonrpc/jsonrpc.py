from asyncio import Future, gather, ensure_future, wait, CancelledError, FIRST_COMPLETED
from typing import Optional, Dict, Any

from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from websockets import WebSocketCommonProtocol as WebSocket

from ._base import JsonrpcBase
from .loggers import logger
from .types import Outgoing, Notifier, Incoming
from ..models import Notification, Response, Request
from ..routing import Route

__all__ = [
    'Jsonrpc',
]


# TODO middleware
class Jsonrpc(JsonrpcBase):
    def _customs(self, sr: SanicRequest, in_: Incoming, ws: Optional[WebSocket] = None) -> Dict[type, Any]:
        return {
            SanicRequest: sr,
            WebSocket: ws,
            Sanic: self.app,
            Request: in_,
            Notification: in_,
            Incoming: in_,
            Notifier: self._notifier(ws) if ws else None,
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
        return ensure_future(ws.send(self._serialize(dict(outgoing))))

    async def _ws(self, sanic_request: SanicRequest, ws: WebSocket):
        recv = None
        pending = set()

        while True:
            if recv not in pending:
                recv = ensure_future(ws.recv())
                pending.add(recv)

            try:
                done, pending = await wait(pending, return_when=FIRST_COMPLETED)
            except CancelledError:
                # TODO test pending futures while closing WS
                for fut in pending:
                    self._finalise_future(fut)

                break

            for fut in done:
                # TODO test exception in call
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

                fut = self._register_call(incoming, route, self._customs(sanic_request, incoming, ws))

                if isinstance(incoming, Request):
                    pending.add(fut)

    def _notifier_done_callback(self, fut: Future):
        self._finalise_future(fut)

        if fut in self._notifications:
            self._notifications.remove(fut)

    def _notifier(self, ws: WebSocket) -> Notifier:
        def notifier(notification: Notification) -> Future:
            if not isinstance(notification, Notification):
                # TODO test invalid usage
                raise TypeError("Notifier's arg must be a Notification, not {!r}", notification.__class__.__name__)

            # TODO test outgoing notifications
            fut = self._ws_outgoing(ws, notification)
            fut.add_done_callback(self._notifier_done_callback)
            # TODO test no leak
            self._notifications.add(fut)
            return fut
        return notifier

    async def _stop_processing(self, _app, _loop):
        await super()._stop_processing(_app, _loop)

        for fut in self._notifications:
            self._finalise_future(fut)

    def __init__(self, app: Sanic, post_route: Optional[str] = None, ws_route: Optional[str] = None):
        super().__init__()
        self.app = app
        self._notifications = set()
        self._processing_task = None
        app.listener('after_server_start')(self._start_processing)
        app.listener('before_server_stop')(self._stop_processing)

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)
