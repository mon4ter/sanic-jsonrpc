from typing import Callable

from sanic_jsonrpc import Jsonrpc


# noinspection PyProtectedMember
def test_jsonrpc():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f():
        ...

    # noinspection PyArgumentList
    @jsonrpc()
    def fb():
        ...

    @jsonrpc.method
    def fm():
        ...

    @jsonrpc.method()
    def fmb():
        ...

    mf = jsonrpc._route_post('f')
    mfb = jsonrpc._route_post('fb')
    mfm = jsonrpc._route_post('fm')
    mfmb = jsonrpc._route_post('fmb')

    assert mf.name == 'f'
    assert isinstance(mf.func, Callable)
    assert mf.func is f
    assert mf.params is None
    assert mf.result is None

    assert mfb.name == 'fb'
    assert mfb.func is fb

    assert mfm.name == 'fm'
    assert mfm.func is fm

    assert mfmb.name == 'fmb'
    assert mfmb.func is fmb


# noinspection PyProtectedMember
def test_name():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc('Func')
    def f():
        ...

    @jsonrpc('FuncB')
    def fb():
        ...

    @jsonrpc.method('FuncM')
    def fm():
        ...

    mf = jsonrpc._route_post('Func')
    mfb = jsonrpc._route_post('FuncB')
    mfm = jsonrpc._route_post('FuncM')

    assert mf.name == 'Func'
    assert mf.func is f

    assert mfb.name == 'FuncB'
    assert mfb.func is fb

    assert mfm.name == 'FuncM'
    assert mfm.func is fm


# noinspection PyProtectedMember
def test_annotation():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f(a: int) -> str:
        return str(a)

    # noinspection PyArgumentList
    @jsonrpc()
    def fb(a: int) -> str:
        return str(a)

    @jsonrpc.method
    def fm(a: int) -> str:
        return str(a)

    @jsonrpc.method()
    def fmb(a: int) -> str:
        return str(a)

    @jsonrpc('FuncN')
    def fn(a: int) -> str:
        return str(a)

    @jsonrpc.method('FuncMN')
    def fmn(a: int) -> str:
        return str(a)

    @jsonrpc
    def fab(a: int, b: int) -> str:
        return str(a) + str(b)

    class Pair:
        def __init__(self, first: int, second: int):
            self.first = int(first)
            self.second = int(second)

    @jsonrpc
    def concat(pair: Pair) -> str:
        return str(pair.first) + str(pair.second)

    mf = jsonrpc._route_post('f')
    mfb = jsonrpc._route_post('fb')
    mfm = jsonrpc._route_post('fm')
    mfmb = jsonrpc._route_post('fmb')
    mfn = jsonrpc._route_post('FuncN')
    mfmn = jsonrpc._route_post('FuncMN')
    mfab = jsonrpc._route_post('fab')
    mconcat = jsonrpc._route_post('concat')

    assert mf.func is f
    assert mf.params == {'a': int}
    assert mf.result is str

    assert mfb.func is fb
    assert mfb.params == {'a': int}
    assert mfb.result is str

    assert mfm.func is fm
    assert mfm.params == {'a': int}
    assert mfm.result is str

    assert mfmb.func is fmb
    assert mfmb.params == {'a': int}
    assert mfmb.result is str

    assert mfn.func is fn
    assert mfn.params == {'a': int}
    assert mfn.result is str

    assert mfmn.func is fmn
    assert mfmn.params == {'a': int}
    assert mfmn.result is str

    assert mfab.func is fab
    assert mfab.params == {'a': int, 'b': int}

    assert mfab.func is fab
    assert mfab.params == {'a': int, 'b': int}

    assert mconcat.func is concat
    assert mconcat.params == {'pair': Pair}


# TODO Test params and result override using deco parameters
# TODO Test post and ws decorators
