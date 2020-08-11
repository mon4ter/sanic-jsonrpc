from typing import Any

from fashionable import UNSET, validate

__all__ = [
    'Arg',
    'ArgError',
    'InvalidArgError',
    'MissingArgError',
]


class Arg:
    __slots__ = ('name', 'type', 'default', 'is_positional', 'is_zipped')

    def __init__(self, name: str, type_: type, default: Any, is_positional: bool, is_zipped: bool):
        self.name = name
        self.type = type_
        self.default = default
        self.is_positional = is_positional
        self.is_zipped = is_zipped

    def __repr__(self) -> str:
        return '{}({}{}: {}{})'.format(
            self.__class__.__name__,
            {
                (True, True): '*',
                (True, False): '',
                (False, True): '**',
                (False, False): '*, ',
            }[self.is_positional, self.is_zipped],
            self.name,
            self.type,
            '' if self.default is UNSET else ' = {!r}'.format(self.default),
        )

    def validate(self, value: Any) -> Any:
        if value is UNSET:
            if self.default is UNSET:
                raise MissingArgError(self)
            else:
                result = self.default
        else:
            try:
                result = validate(self.type, value)
            except (TypeError, ValueError, AttributeError) as exc:
                raise InvalidArgError(self, value) from exc

        return result


class ArgError(Exception):
    def __init__(self, fmt: str, arg: Arg, value: Any = UNSET):
        super().__init__(fmt.format(arg=arg, value=value))
        self.arg = arg
        self.value = value


class MissingArgError(ArgError):
    def __init__(self, *args, **kwargs):
        super().__init__("missing required argument {arg.name!r} value", *args, **kwargs)


class InvalidArgError(ArgError):
    def __init__(self, *args, **kwargs):
        super().__init__("invalid argument {arg.name!r} value {value!r}", *args, **kwargs)
