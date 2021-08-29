from typing import Any, Union

from fashionable import Attribute

from ._jsonrpc import _Jsonrpc

__all__ = [
    'Request',
]


class Request(_Jsonrpc):
    method = Attribute(str, strict=True, case_insensitive=False)
    params = Attribute(Any, case_insensitive=False)
    id = Attribute(Union[str, int], strict=True, case_insensitive=False)
