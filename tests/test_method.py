from typing import Callable

from sanic_jsonrpc import Jsonrpc


def test_jsonrpc():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f():
        ...

    assert 'f' in jsonrpc._methods
    assert isinstance(jsonrpc._methods['f'][0], Callable)
    assert jsonrpc._methods['f'][1] is None
    assert jsonrpc._methods['f'][2] is None


def test_method():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc.method
    def f():
        ...

    assert 'f' in jsonrpc._methods
    assert isinstance(jsonrpc._methods['f'][0], Callable)
    assert jsonrpc._methods['f'][1] is None
    assert jsonrpc._methods['f'][2] is None


def test_name():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc('Func1')
    def f():
        ...

    @jsonrpc.method('Func2')
    def f():
        ...

    assert 'Func1' in jsonrpc._methods
    assert 'Func2' in jsonrpc._methods
    assert jsonrpc._methods['Func1'][0].__name__ == 'Func1'
    assert jsonrpc._methods['Func2'][0].__name__ == 'Func2'
    assert jsonrpc._methods['Func1'][0] != jsonrpc._methods['Func2'][0]


def test_annotation():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f(a: int) -> str:
        ...

    @jsonrpc.method
    def fm(a: int) -> str:
        ...

    @jsonrpc('fn')
    def f(a: int) -> str:
        ...

    @jsonrpc.method('fmn')
    def f(a: int) -> str:
        ...

    @jsonrpc
    def fab(a: int, b: int) -> str:
        ...

    class Pair:
        def __init__(self, first: int, second: int):
            self.first = int(first)
            self.second = int(second)

    @jsonrpc
    def concat(pair: Pair) -> str:
        ...

    assert jsonrpc._methods['f'][1] == {'a': int}
    assert jsonrpc._methods['f'][2] is str
    assert jsonrpc._methods['fm'][1] == {'a': int}
    assert jsonrpc._methods['fm'][2] is str
    assert jsonrpc._methods['fn'][1] == {'a': int}
    assert jsonrpc._methods['fn'][2] is str
    assert jsonrpc._methods['fmn'][1] == {'a': int}
    assert jsonrpc._methods['fmn'][2] is str
    assert jsonrpc._methods['fab'][1] == {'a': int, 'b': int}
    assert jsonrpc._methods['concat'][1] == {'pair': Pair}


def test_params_result():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc(None, int, str)
    def f(a):
        ...

    @jsonrpc.method(params=int, result=str)
    def fm(a):
        ...

    @jsonrpc(result=str)
    def fr(a: int) -> int:
        ...

    @jsonrpc.method(result=str)
    def fmr(a: int) -> int:
        ...

    assert jsonrpc._methods['f'][1] == {0: int}
    assert jsonrpc._methods['f'][2] is str
    assert jsonrpc._methods['fm'][1] == {0: int}
    assert jsonrpc._methods['fm'][2] is str
    assert jsonrpc._methods['fr'][1] == {'a': int}
    assert jsonrpc._methods['fr'][2] is str
    assert jsonrpc._methods['fmr'][1] == {'a': int}
    assert jsonrpc._methods['fmr'][2] is str
