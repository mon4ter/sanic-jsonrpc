from enum import Enum

__all__ = [
    'Transports',
]


class Transports(Enum):
    post = 1
    ws = 2
