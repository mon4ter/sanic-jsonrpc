from copy import copy
from typing import Dict, Optional, Union

from sanic import Sanic
from sanic.request import Request as SanicRequest
from websockets import WebSocketCommonProtocol as WebSocket

from ._middleware import Directions, Objects, Transports
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
        '_incoming', '_outgoing', '_websocket', '_notifier', '_dict',
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

        self._dict = None

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
                new._direction = value
            elif isinstance(value, Notification):
                new._object = Objects.notification
                new._notification = value

                if self._direction is Directions.outgoing:
                    new._outgoing = value
                else:
                    new._direction = Directions.incoming
                    new._incoming = value

        return new

    @property
    def direction(self) -> Directions:
        return self._direction

    @property
    def transport(self) -> Transports:
        return self._transport

    @property
    def object(self) -> Objects:
        return self._object

    @property
    def dict(self) -> Dict[type, ContextValue]:
        if self._dict is None:
            self._dict = {
                Sanic: self._sanic,
                SanicRequest: self._sanic_request,
                Directions: self._direction,
                Transports: self._transport,
                Objects: self._object,
                WebSocket: self._websocket, Optional[WebSocket]: self._websocket,
                Notifier: self._notifier, Optional[Notifier]: self._notifier,
                Request: self._request, Optional[Request]: self._request,
                Response: self._response, Optional[Response]: self._response,
                Notification: self._notification, Optional[Notification]: self._notification,
                Incoming: self._incoming, Optional[Incoming]: self._incoming,
                Outgoing: self._outgoing, Optional[Outgoing]: self._outgoing,
            }

        return self._dict

    @property
    def incoming(self) -> Optional[Incoming]:
        return self._incoming

    @property
    def notification(self) -> Optional[Notification]:
        return self._notification

    @property
    def outgoing(self) -> Optional[Outgoing]:
        return self._outgoing

    @property
    def websocket(self) -> Optional[WebSocket]:
        return self._websocket
