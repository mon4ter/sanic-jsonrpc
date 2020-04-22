from asyncio import iscoroutine
from inspect import Parameter, Signature, signature
from typing import Any, Callable, Dict, Optional, Tuple

from fashionable import UNSET

from .arg import Arg, ArgError

__all__ = [
    'ResultError',
    'Route',
]


class Route:
    __slots__ = ('func', 'method', 'args', 'result')

    _POSITIONAL_KINDS = {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD, Parameter.VAR_POSITIONAL}
    _ZIPPED_KINDS = {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}

    @classmethod
    def from_inspect(cls, func: Callable, method: Optional[str], annotations: Dict[str, type]) -> 'Route':
        if not method:
            method = func.__name__

        sign = signature(func)

        args = tuple(Arg(
            parameter.name,
            Any if parameter.annotation is Parameter.empty else parameter.annotation,
            UNSET if parameter.default is Parameter.empty else parameter.default,
            parameter.kind in cls._POSITIONAL_KINDS,
            parameter.kind in cls._ZIPPED_KINDS
        ) for parameter in sign.parameters.values())

        return_annotation = sign.return_annotation
        result_type = annotations.get('result', Any if return_annotation is Signature.empty else return_annotation)
        result = Arg('result', result_type, UNSET, False, False) if result_type else None

        return cls(func, method, args, result)

    def __init__(self, func: Callable, method: str, args: Tuple[Arg, ...], result: Optional[Arg]):
        self.func = func
        self.method = method
        self.args = args
        self.result = result

    def _validate(self, params: Any, customs: Dict[type, Any]) -> Tuple[list, dict]:
        list_params = []
        dict_params = {}

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
                for param_name in list(dict_params):
                    kwargs[param_name] = arg.validate(dict_params.pop(param_name))
                    recover_allowed = False

                while list_params:
                    args.append(arg.validate(list_params.pop(0)))
                    recover_allowed = False

                continue

            value = customs.get(arg.type, UNSET)

            name = arg.name

            if value is UNSET:
                try:
                    value = arg.validate(
                        dict_params.pop(name, UNSET) if dict_params else list_params.pop(0) if list_params else UNSET
                    )
                except ArgError:
                    if not recover_allowed:
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
