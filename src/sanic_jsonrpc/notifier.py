from asyncio import Future, ensure_future
from typing import Any, Callable

from websockets import WebSocketCommonProtocol as WebSocket

from .models import Notification

__all__ = [
    'Notifier',
]

_Sender = Callable[[Notification], Future]
_Finalizer = Callable[[Future], Any]


# TODO Add SSE support
class Notifier:
    def __init__(self, ws: WebSocket, sender: _Sender, finalizer: _Finalizer):
        self._ws = ws
        self._sender = sender
        self._finalizer = finalizer
        self._pending = set()

    @property
    def closed(self) -> bool:
        return self._ws.closed

    def _done_callback(self, fut: Future):
        self._finalizer(fut)

        if fut in self._pending:
            self._pending.remove(fut)

    def send(self, notification: Notification) -> Future:
        fut = self._sender(notification) if self._ws.open else ensure_future(self._ws.ensure_open())
        fut.add_done_callback(self._done_callback)
        self._pending.add(fut)
        return fut

    def cancel(self):
        for fut in self._pending:
            fut.cancel()
