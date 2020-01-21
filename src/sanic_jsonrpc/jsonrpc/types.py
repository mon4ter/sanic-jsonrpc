from asyncio import Future
from typing import Union, Callable

from ..models import Notification, Request, Response

__all__ = [
    'AnyJsonrpc',
    'Incoming',
    'Notifier',
    'Outgoing',
]

Incoming = Union[Request, Notification]
Outgoing = Union[Response, Notification]
AnyJsonrpc = Union[Incoming, Outgoing]
Notifier = Callable[[Notification], Future]
