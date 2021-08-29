from typing import Any

from fashionable import Attribute

from ._jsonrpc import _Jsonrpc

__all__ = [
    'Notification',
]


class Notification(_Jsonrpc):
    method = Attribute(str, strict=True, case_insensitive=False)
    params = Attribute(Any, case_insensitive=False)
