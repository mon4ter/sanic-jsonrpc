from asyncio import Future, ensure_future
from typing import Callable, Any

from websockets import WebSocketCommonProtocol as WebSocket

from .models import Notification

__all__ = [
    'Notifier',
]

_Sender = Callable[[WebSocket, Notification], Future]
_Finalizer = Callable[[Future], Any]


class Notifier:
    def __init__(self, ws: WebSocket, sender: _Sender, finalizer: _Finalizer):
        # TODO Deny manual instantiation
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
        if self.closed:
            return ensure_future(self._ws.ensure_open())

        fut = self._sender(self._ws, notification)
        fut.add_done_callback(self._done_callback)
        self._pending.add(fut)
        return fut

    def cancel(self):
        for fut in self._pending:
            fut.cancel()
