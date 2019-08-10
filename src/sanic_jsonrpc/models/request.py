from typing import Union

from fashionable import Attribute

from .notification import Notification

__all__ = [
    'Request',
]


class Request(Notification):
    id = Attribute(Union[str, int], strict=True)
