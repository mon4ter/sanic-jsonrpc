from typing import Optional

from fashionable import Attribute, Model, ModelValueError

__all__ = [
    '_Jsonrpc',
]


class _Jsonrpc(Model):
    jsonrpc = Attribute(Optional[str], strict=True, default='2.0')

    def __init__(self, *args, **kwargs):
        if args and args[0] != '2.0':
            args = ('2.0',) + args

        super().__init__(*args, **kwargs)

        if self.jsonrpc != '2.0':
            raise ModelValueError(
                'Invalid %(model)s: invalid attribute jsonrpc: MUST be exactly "2.0"', model=self.__class__.__name__
            )
