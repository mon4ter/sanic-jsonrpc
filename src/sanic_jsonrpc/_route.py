from collections import OrderedDict
from inspect import getfullargspec
from typing import Any, Callable, Dict, Optional

__all__ = [
    '_Route',
]

_Annotations = Dict[str, type]


class _Route:
    __slots__ = ('func', 'name', 'args', 'varargs', 'kwargs', 'varkw', 'result')

    @classmethod
    def from_inspect(cls, func: Callable, name: Optional[str], annotations: _Annotations) -> '_Route':
        name = name or func.__name__

        spec = getfullargspec(func)

        args = OrderedDict(
            (arg_name, annotations.get(arg_name, spec.annotations.get(arg_name, Any)))
            for arg_name in spec.args
        )

        kwargs = OrderedDict(
            (arg_name, annotations.get(arg_name, spec.annotations.get(arg_name, Any)))
            for arg_name in spec.kwonlyargs
        )

        varargs = annotations.get(spec.varargs, spec.annotations.get(spec.varargs, Any)) if spec.varargs else None

        varkw = annotations.get(spec.varkw, spec.annotations.get(spec.varkw, Any)) if spec.varkw else None

        result = annotations.get('result', spec.annotations.get('return'))

        return cls(func, name, args, varargs, kwargs, varkw, result)

    def __init__(
            self,
            func: Callable,
            name: str,
            args: _Annotations,
            varargs: Optional[type],
            kwargs: _Annotations,
            varkw: Optional[type],
            result: Optional[type]
    ):
        self.func = func
        self.name = name
        self.args = args
        self.varargs = varargs
        self.kwargs = kwargs
        self.varkw = varkw
        self.result = result
