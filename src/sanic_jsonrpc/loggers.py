from logging import getLogger

__all__ = [
    'error_logger',
    'logger',
    'traffic_logger',
]

# TODO Access logger
logger = getLogger(__package__ + '.root')
error_logger = getLogger(__package__ + '.error')
traffic_logger = getLogger(__package__ + '.traffic')
