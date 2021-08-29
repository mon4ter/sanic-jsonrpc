from fashionable import Attribute, Model, ModelValueError

__all__ = [
    '_Jsonrpc',
]


class _Jsonrpc(Model):
    jsonrpc = Attribute(str, strict=True, default='2.0', case_insensitive=False)

    def __init__(self, *args, **kwargs):
        if args and args[0] != '2.0':
            args = ('2.0',) + args

        super().__init__(*args, **kwargs)

        if self.jsonrpc != '2.0':
            raise ModelValueError('MUST be exactly "2.0"', model=type(self).__name__, attr='jsonrpc')
