from typing import Any, Optional, Union

from fashionable import Attribute

from .error import Error
from ._jsonrpc import _Jsonrpc

__all__ = [
    'Response',
]


class Response(_Jsonrpc):
    result = Attribute(Any)
    error = Attribute(Optional[Error])
    id = Attribute(Optional[Union[str, int]], strict=True, default=None)
