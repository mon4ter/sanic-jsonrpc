from copy import copy
from typing import Generator, Optional, Tuple, Union

from sanic import Sanic
from sanic.request import Request as SanicRequest
from websockets import WebSocketCommonProtocol as WebSocket

from ._middleware import Directions, Transports, Objects
from .models import Notification, Request, Response
from .notifier import Notifier
from .types import AnyJsonrpc, Incoming, Outgoing

__all__ = [
    'Context',
    'ContextValue',
    'MutableContextValue',
]

MutableContextValue = Union[AnyJsonrpc, Directions]
ContextValue = Union[Sanic, SanicRequest, WebSocket, Notifier, Transports, Objects, MutableContextValue]


class Context:
    __slots__ = (
        '_sanic', '_sanic_request', '_direction', '_transport', '_object', '_request', '_response', '_notification',
        '_incoming', '_outgoing', '_websocket', '_notifier'
    )

    def __init__(
            self,
            sanic: Sanic,
            sanic_request: SanicRequest,
            websocket: Optional[WebSocket] = None,
            notifier: Optional[Notifier] = None,
    ):
        self._sanic = sanic
        self._sanic_request = sanic_request
        self._websocket = websocket
        self._notifier = notifier

        self._direction = None
        self._transport = Transports.ws if websocket else Transports.post
        self._object = None

        self._request = None
        self._response = None
        self._notification = None
        self._incoming = None
        self._outgoing = None

    def __copy__(self) -> 'Context':
        new = type(self)(self._sanic, self._sanic_request, self._websocket, self._notifier)
        new._direction = self._direction
        new._object = self._object
        new._request = self._request
        new._response = self._response
        new._notification = self._notification
        new._incoming = self._incoming
        new._outgoing = self._outgoing
        return new

    def __call__(self, *values: MutableContextValue) -> 'Context':
        new = copy(self)

        for value in values:
            if isinstance(value, Request):
                new._direction = Directions.incoming
                new._object = Objects.request
                new._request = value
                new._incoming = value
            elif isinstance(value, Response):
                new._direction = Directions.outgoing
                new._object = Objects.response
                new._response = value
                new._outgoing = value
            elif isinstance(value, Directions):
                self._direction = value
            elif isinstance(value, Notification):
                new._object = Objects.notification
                new._notification = value

                if self._direction is Directions.outgoing:
                    new._outgoing = value
                else:
                    new._direction = Directions.incoming
                    new._incoming = value

        return new

    def __iter__(self) -> Generator[Tuple[type, ContextValue], None, None]:
        yield Sanic, self._sanic
        yield SanicRequest, self._sanic_request
        yield Directions, self._direction
        yield Transports, self._transport
        yield Objects, self._object

        yield Request, self._request
        yield Optional[Request], self._request
        yield Response, self._response
        yield Optional[Response], self._response
        yield Notification, self._notification
        yield Optional[Notification], self._notification
        yield Incoming, self._incoming
        yield Optional[Incoming], self._incoming
        yield Outgoing, self._outgoing
        yield Optional[Outgoing], self._outgoing
        yield WebSocket, self._websocket
        yield Optional[WebSocket], self._websocket
        yield Notifier, self._notifier
        yield Optional[Notifier], self._notifier

    @property
    def direction(self) -> Directions:
        return self._direction

    @property
    def transport(self) -> Transports:
        return self._transport

    @property
    def object(self) -> Objects:
        return self._object
