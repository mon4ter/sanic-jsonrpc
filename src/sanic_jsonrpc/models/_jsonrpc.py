from fashionable import Attribute, Model, ModelValueError

__all__ = [
    '_Jsonrpc',
]


class _Jsonrpc(Model):
    jsonrpc = Attribute(str, strict=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.jsonrpc != '2.0':
            raise ModelValueError(
                'Invalid %(model)s: invalid attribute jsonrpc: MUST be exactly "2.0"', model=self.__class__.__name__
            )
