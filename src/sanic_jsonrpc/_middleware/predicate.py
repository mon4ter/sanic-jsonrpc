from typing import Set

from .directions import Directions
from .objects import Objects
from .transports import Transports

__all__ = [
    'Predicate',
]


class Predicate:
    __slots__ = ('directions', 'transports', 'objects')

    def __init__(self, directions: Set[Directions], transports: Set[Transports], objects: Set[Objects]):
        self.directions = directions
        self.transports = transports
        self.objects = objects
