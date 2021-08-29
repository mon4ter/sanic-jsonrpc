from typing import Any, Optional, Union

from fashionable import Attribute

from .error import Error
from ._jsonrpc import _Jsonrpc

__all__ = [
    'Response',
]


class Response(_Jsonrpc):
    result = Attribute(Any, case_insensitive=False)
    error = Attribute(Optional[Error], case_insensitive=False)
    id = Attribute(Optional[Union[str, int]], strict=True, default=None, case_insensitive=False)
