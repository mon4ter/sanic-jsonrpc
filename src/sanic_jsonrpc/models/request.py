from typing import Union

from fashionable import Attribute

from .notification import Notification

__all__ = [
    'Request',
    'RequestId',
]

RequestId = Union[str, int]


class Request(Notification):
    id = Attribute(RequestId, strict=True)
