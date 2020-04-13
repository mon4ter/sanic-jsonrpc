from enum import Enum

__all__ = [
    '_Transports',
]


class _Transports(Enum):
    post = 1
    ws = 2
