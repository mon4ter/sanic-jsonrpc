from asyncio import CancelledError, FIRST_COMPLETED, Future, ensure_future, gather, wait
from time import monotonic
from typing import Any, Dict, Optional

from fashionable import UNSET
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse
from websockets import WebSocketCommonProtocol as WebSocket

from ._basejsonrpc import BaseJsonrpc
from .._listening import Directions, Events, Objects, Transports
from .._routing import Route
from ..loggers import access_logger, error_logger, logger, traffic_logger
from ..models import Notification, Request, Response
from ..notifier import Notifier
from ..types import Incoming, Outgoing

__all__ = [
    'Events',
    'Jsonrpc',
    'SanicJsonrpc',
]


# TODO Test listeners
class SanicJsonrpc(BaseJsonrpc):
    def _customs(
            self,
            sanic_request: SanicRequest,
            incoming: Optional[Incoming] = None,
            ws: Optional[WebSocket] = None,
            notifier: Optional[Notifier] = None,
            outgoing: Optional[Outgoing] = None
    ) -> Dict[type, Any]:
        return {
            SanicRequest: sanic_request,
            WebSocket: ws,
            Sanic: self.app,
            Request: incoming,
            Notification: incoming or outgoing,
            Incoming: incoming,
            Notifier: notifier,
            Outgoing: outgoing,
            Response: outgoing,
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

            fut = self._register_call(incoming, route, self._customs(sanic_request, incoming), is_post=True)

            if isinstance(incoming, Request):
                futures.append(fut)

        for response in await gather(*futures):
            responses.append(response)

        body = self._serialize_responses(responses, single)
        content_type = 'application/json' if body else 'text/plain'
        return HTTPResponse(body, 207, content_type=content_type)

    def _ws_outgoing(self, ws: WebSocket, outgoing: Outgoing) -> Future:
        return ensure_future(ws.send(self._serialize(dict(outgoing))))

    async def _ws_notification(self, ws: WebSocket, notification: Notification, customs: Dict[type, Any]):
        try:
            await self._run_listeners(Directions.outgoing, Transports.ws, Objects.notification, customs)
        except Exception as err:
            error_logger.error("Listeners after %r failed: %s", notification, err, exc_info=err)
        else:
            traffic_logger.debug("<-- %r", notification)
            await self._ws_outgoing(ws, notification)

    async def _ws(self, sanic_request: SanicRequest, ws: WebSocket):
        recv = None
        pending = set()

        def sender(notification: Notification) -> Future:
            customs = self._customs(sanic_request, None, ws, notifier, notification)
            return ensure_future(self._ws_notification(ws, notification, customs))

        notifier = Notifier(ws, sender, self._finalise_future)

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

                fut = self._register_call(
                    incoming,
                    route,
                    self._customs(sanic_request, incoming, ws, notifier),
                    is_post=False,
                )

                if isinstance(incoming, Request):
                    pending.add(fut)

        notifier.cancel()

        for fut in pending:
            fut.cancel()

    def __init__(
            self,
            app: Sanic,
            post_route: Optional[str] = None,
            ws_route: Optional[str] = None,
            *,
            access_log: bool = True
    ):
        super().__init__()
        self.app = app
        self._processing_task = None
        app.listener('after_server_start')(self._start_processing)
        app.listener('before_server_stop')(self._stop_processing)

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        if access_log:
            @self.listener(Events.request)
            def set_time(req: Request, sanic_req: SanicRequest):
                key = 'sanic-jsonrpc_time_{}'.format(req.id)
                sanic_req[key] = monotonic()

            @self.listener(Events.response)
            def log_response(req: Request, res: Response, sanic_req: SanicRequest):
                key = 'sanic-jsonrpc_time_{}'.format(req.id)
                start = sanic_req.pop(key)
                access_logger.info("", extra={
                    'method': req.method,
                    'id': req.id,
                    'time': '{:.6f}'.format((monotonic() - start) * 1000),
                    'error': res.error.code if res.error is not UNSET else '',
                })


class Jsonrpc(SanicJsonrpc):
    def __init__(self, *args, **kwargs):
        from warnings import warn
        warn(
            "Class {} has been renamed to {}".format(self.__class__.__name__, self.__class__.__base__.__name__),
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
