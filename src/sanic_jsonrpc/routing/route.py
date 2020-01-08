from asyncio import iscoroutine
from inspect import getfullargspec
from itertools import zip_longest
from typing import Any, Callable, Dict, Optional, Tuple, Union

from fashionable import UNSET

from .arg import Arg, ArgError

__all__ = [
    'ResultError',
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

        result_type = annotations.get('result', spec.annotations.get('return'))
        result = Arg('result', result_type, UNSET, False, False) if result_type else None

        return cls(func, name or func.__name__, tuple(args), result)

    def __init__(self, func: Callable, name: str, args: Tuple[Arg], result: Optional[Arg]):
        self.func = func
        self.name = name
        self.args = args
        self.result = result

    def _validate(self, params: Union[list, dict], customs: Optional[dict] = None) -> Tuple[list, dict]:
        if customs is None:
            customs = {}

        list_params = None
        dict_params = None

        if isinstance(params, list):
            list_params = params.copy()
        elif isinstance(params, dict):
            dict_params = params.copy()
        else:
            list_params = [params]

        args = []
        kwargs = {}
        recover_allowed = True

        for arg in self.args:
            if arg.is_zipped:
                if dict_params:
                    for param_name, param_value in dict_params.items():
                        kwargs[param_name] = arg.validate(param_value)
                        recover_allowed = False
                else:
                    for param_value in list_params:
                        args.append(arg.validate(param_value))
                        recover_allowed = False

                continue

            value = customs.get(arg.type, UNSET)

            # TODO test default arg
            # TODO test default kwarg
            name = arg.name

            if value is UNSET:
                try:
                    value = arg.validate(
                        dict_params.pop(name, UNSET) if dict_params else list_params.pop(0) if list_params else UNSET
                    )
                except ArgError:
                    if not recover_allowed:
                        # TODO test recover once
                        raise

                    value = arg.validate(params)

            if arg.is_positional:
                args.append(value)
            else:
                kwargs[name] = value

            recover_allowed = False

        return args, kwargs

    async def call(self, *args, **kwargs) -> Any:
        args, kwargs = self._validate(*args, **kwargs)
        ret = self.func(*args, **kwargs)

        if iscoroutine(ret):
            ret = await ret

        if self.result:
            try:
                ret = self.result.validate(ret)
            except ArgError as err:
                raise ResultError(err.arg, ret) from err

        return ret


class ResultError(ArgError):
    def __init__(self, *args, **kwargs):
        super().__init__("invalid call result value {value!r}", *args, **kwargs)
