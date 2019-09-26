from collections import OrderedDict
from inspect import getfullargspec
from typing import Any, Callable, Dict, List, Optional, Tuple

from fashionable import validate
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.websocket import WebSocketCommonProtocol

from .models import Notification, Request

__all__ = [
    '_Route',
    'Notifier',
]

Notifier = Callable[[Notification], None]

_Annotations = Dict[str, type]
_SPECIALS = SanicRequest, WebSocketCommonProtocol, Sanic, Request, Notification, Notifier


class _Route:
    @classmethod
    def from_inspect(cls, func: Callable, name: Optional[str], annotations: _Annotations) -> '_Route':
        name = name or func.__name__

        spec = getfullargspec(func)

        args = OrderedDict(
            (arg_name, annotations.get(arg_name, spec.annotations.get(arg_name, Any)))
            for arg_name in spec.args
        )

        varargs = annotations.get(spec.varargs, spec.annotations.get(spec.varargs, Any)) if spec.varargs else None

        varkw = annotations.get(spec.varkw, spec.annotations.get(spec.varkw, Any)) if spec.varkw else None

        result = annotations.get('result', spec.annotations.get('return'))

        return cls(func, name, args, varargs, varkw, result)

    def __init__(
            self,
            func: Callable,
            name: str,
            args: _Annotations,
            varargs: Optional[type],
            varkw: Optional[type],
            result: Optional[type]
    ):
        self._varargs = varargs
        self._varkw = varkw
        self.func = func
        self.name = name
        self.args = args
        self.result = result

    def validate(self, args: List, kwargs: Dict) -> Tuple[List, Dict]:
        # TODO test args after specials
        for name, value in zip((n for n in self.args if n not in kwargs), args.copy()):
            kwargs[name] = value
            args.remove(value)

        # TODO if single arg try arg(*args, **kwargs)

        result_args = [validate(self._varargs, v) for v in args]

        result_kwargs = {
            n: v if t in _SPECIALS else validate(t, v)
            for n, t, v in ((n, t, kwargs.pop(n)) for n, t in self.args.items())
        }

        # TODO test varkw
        result_kwargs.update({n: validate(self._varkw, v) for n, v in kwargs.items()})

        return result_args, result_kwargs
