from logging import getLogger

__all__ = [
    'access_logger',
    'error_logger',
    'logger',
    'traffic_logger',
]

logger = getLogger(__package__ + '.root')
error_logger = getLogger(__package__ + '.error')
traffic_logger = getLogger(__package__ + '.traffic')
access_logger = getLogger(__package__ + '.access')
