from inspect import getfullargspec
from itertools import zip_longest
from typing import Any, Callable, Dict, Optional, Tuple

from fashionable import UNSET

from .arg import Arg

__all__ = [
    'Route',
]


class Route:
    __slots__ = ('func', 'name', 'args', 'result')

    @classmethod
    def from_inspect(cls, func: Callable, name: Optional[str], annotations: Dict[str, type]) -> 'Route':
        spec = getfullargspec(func)

        def typ(nam: str) -> type:
            return annotations.get(nam, spec.annotations.get(nam, Any))

        args = [
            Arg(n, typ(n), d, is_positional, is_zipped=False)
            for names, defaults, is_positional in (
                (spec.args or (), spec.defaults or (), True),
                (spec.kwonlyargs or (), spec.kwonlydefaults or (), False),
            )
            for n, d in reversed(tuple(zip_longest(reversed(names), reversed(defaults), fillvalue=UNSET)))
        ]

        if spec.varargs:
            args.append(Arg(spec.varargs, typ(spec.varargs), UNSET, is_positional=True, is_zipped=True))

        if spec.varkw:
            args.append(Arg(spec.varkw, typ(spec.varkw), UNSET, is_positional=False, is_zipped=True))

        result = annotations.get('result', spec.annotations.get('return'))

        return cls(func, name or func.__name__, tuple(args), result)

    def __init__(self, func: Callable, name: str, args: Tuple[Arg], result: Optional[type]):
        self.func = func
        self.name = name
        self.args = args
        self.result = result
