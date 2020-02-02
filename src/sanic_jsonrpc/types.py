from typing import Union

from .models import Notification, Request, Response

__all__ = [
    'AnyJsonrpc',
    'Incoming',
    'Outgoing',
]

Incoming = Union[Request, Notification]
Outgoing = Union[Response, Notification]
AnyJsonrpc = Union[Incoming, Outgoing]
