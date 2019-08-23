from .models import Error

__all__ = [
    'INTERNAL_ERROR',
    'INVALID_PARAMS',
    'INVALID_REQUEST',
    'METHOD_NOT_FOUND',
    'PARSE_ERROR',
]

PARSE_ERROR = Error(-32700, "Parse error")
INVALID_REQUEST = Error(-32600, "Invalid Request")
METHOD_NOT_FOUND = Error(-32601, "Method not found")
INVALID_PARAMS = Error(-32602, "Invalid params")
INTERNAL_ERROR = Error(-32603, "Internal error")
