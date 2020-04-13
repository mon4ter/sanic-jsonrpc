from typing import Set

from ._directions import _Directions
from ._objects import _Objects
from ._transports import _Transports

__all__ = [
    '_Event',
]


class _Event:
    __slots__ = ('directions', 'transports', 'objects')

    def __init__(self, directions: Set[_Directions], transports: Set[_Transports], objects: Set[_Objects]):
        self.directions = directions
        self.transports = transports
        self.objects = objects
