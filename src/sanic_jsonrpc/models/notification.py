from typing import Any

from fashionable import Attribute

from .jsonrpc import Jsonrpc

__all__ = [
    'Notification',
]


class Notification(Jsonrpc):
    method = Attribute(str, strict=True)
    params = Attribute(Any)
