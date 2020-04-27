from typing import Any, Union

from fashionable import Attribute

from ._jsonrpc import _Jsonrpc

__all__ = [
    'Request',
]


class Request(_Jsonrpc):
    method = Attribute(str, strict=True)
    params = Attribute(Any)
    id = Attribute(Union[str, int], strict=True)
