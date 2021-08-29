from typing import Any

from fashionable import Attribute, Model

__all__ = [
    'Error',
]


class Error(Model, Exception):
    code = Attribute(int, case_insensitive=False)
    message = Attribute(str, case_insensitive=False)
    data = Attribute(Any, case_insensitive=False)
