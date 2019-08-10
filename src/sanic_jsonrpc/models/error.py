from typing import Any

from fashionable import Attribute, Model

__all__ = [
    'Error',
]


class Error(Model):
    code = Attribute(int)
    message = Attribute(str)
    data = Attribute(Any)
