from asyncio import CancelledError, FIRST_COMPLETED, Future, ensure_future, gather, wait
from http import HTTPStatus
from time import monotonic
from typing import Any, Optional

from fashionable import UNSET
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.response import HTTPResponse, json
from websockets import WebSocketCommonProtocol as WebSocket

from ._basejsonrpc import BaseJsonrpc
from .._context import Context
from .._middleware import Directions, Predicates
from ..loggers import access_logger, error_logger, traffic_logger
from ..models import Notification, Request, Response
from ..notifier import Notifier

__all__ = [
    'Jsonrpc',
    'Predicates',
    'SanicJsonrpc',
]


class SanicJsonrpc(BaseJsonrpc):
    @staticmethod
    def _sanic_request_set(req: SanicRequest, key: str, value: Any):
        if hasattr(req, 'ctx'):
            setattr(req.ctx, key, value)
        elif isinstance(req, dict):
            req[key] = value

    @staticmethod
    def _sanic_request_pop(req: SanicRequest, key: str) -> Any:
        value = None

        if hasattr(req, 'ctx'):
            value = getattr(req.ctx, key)
            delattr(req.ctx, key)
        elif isinstance(req, dict):
            value = req[key]
            del req[key]

        return value

    @classmethod
    def _ws_outgoing(cls, ctx: Context) -> Future:
        return ensure_future(ctx.websocket.send(cls._serialize(ctx.outgoing)))

    async def _post(self, sanic_request: SanicRequest) -> HTTPResponse:
        ctx = Context(self.app, sanic_request)

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

            if not self._handle_incoming(ctx(incoming), responses.append, futures.append):
                continue

        for response in await gather(*futures):
            responses.append(response)

        if responses:
            sanic_response = json(responses[0] if single else responses, HTTPStatus.MULTI_STATUS, dumps=self._serialize)
        else:
            sanic_response = HTTPResponse(status=HTTPStatus.NO_CONTENT)

        return sanic_response

    async def _ws_notification(self, ctx: Context):
        try:
            await self._run_middlewares(ctx)
        except Exception as err:
            error_logger.error("Middlewares after outgoing %r failed: %s", ctx.notification, err, exc_info=err)
        else:
            traffic_logger.debug("<-- %r", ctx.notification)
            await self._ws_outgoing(ctx)

    async def _ws(self, sanic_request: SanicRequest, ws: WebSocket):
        recv = None
        pending = set()

        def sender(notification: Notification) -> Future:
            return ensure_future(self._ws_notification(sender_ctx(notification)))

        notifier = Notifier(ws, sender, self._finalise_future)
        root_ctx = Context(self.app, sanic_request, ws, notifier)
        sender_ctx = root_ctx(Directions.outgoing)

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
                    pending.add(self._ws_outgoing(root_ctx(result)))
                    continue

                obj = self._parse_json(result)

                if isinstance(obj, Response):
                    pending.add(self._ws_outgoing(root_ctx(obj)))
                    continue

                incoming = self._parse_message(obj)

                if isinstance(incoming, Response):
                    pending.add(self._ws_outgoing(root_ctx(incoming)))
                    continue

                ctx = root_ctx(incoming)

                if not self._handle_incoming(ctx, lambda x: pending.add(self._ws_outgoing(ctx(x))), pending.add):
                    continue

        notifier.cancel()

        for fut in pending:
            fut.cancel()

    def __init__(
            self,
            app: Sanic,
            post_route: Optional[str] = None,
            ws_route: Optional[str] = None,
            *,
            access_log: bool = True,
            case_insensitive: bool = True
    ):
        super().__init__(case_insensitive=case_insensitive)
        self.app = app
        self._processing_task = None
        app.listener('after_server_start')(self._start_processing)
        app.listener('before_server_stop')(self._stop_processing)

        if post_route:
            self.app.add_route(self._post, post_route, methods=frozenset({'POST'}))

        if ws_route:
            self.app.add_websocket_route(self._ws, ws_route)

        if access_log:
            @self.middleware(Predicates.request)
            def set_time(req: Request, sanic_req: SanicRequest):
                key = 'sanic_jsonrpc-time-{}'.format(req.id)
                self._sanic_request_set(sanic_req, key, monotonic())

            @self.middleware(Predicates.response)
            def log_response(req: Request, res: Response, sanic_req: SanicRequest):
                key = 'sanic_jsonrpc-time-{}'.format(req.id)
                start = self._sanic_request_pop(sanic_req, key)
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
