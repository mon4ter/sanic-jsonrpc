from typing import Callable

from sanic_jsonrpc import Jsonrpc


# noinspection PyProtectedMember
def test_jsonrpc():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f():
        ...

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


# noinspection PyProtectedMember,DuplicatedCode
def test_annotation():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def f(a: int) -> str:
        return str(a)

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
    async def concat(pair: Pair) -> str:
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

    assert mconcat.func is concat
    assert mconcat.params == {'pair': Pair}


# noinspection PyProtectedMember,DuplicatedCode
def test_params_result():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc(None, a=int)
    def fp(a):
        return str(a)

    @jsonrpc.method(None, a=int)
    def fmp(a):
        return str(a)

    @jsonrpc(a=int)
    def fpk(a):
        return str(a)

    @jsonrpc.method(a=int)
    def fmpk(a):
        return str(a)

    @jsonrpc(None, result=str)
    def fr(a):
        return str(a)

    @jsonrpc.method(None, result=str)
    def fmr(a):
        return str(a)

    @jsonrpc(result=str)
    def frk(a):
        return str(a)

    @jsonrpc.method(result=str)
    def fmrk(a):
        return str(a)

    @jsonrpc(a=int, b=int, result=str)
    def fab(a, b):
        return str(a) + str(b)

    class Pair:
        def __init__(self, first: int, second: int):
            self.first = int(first)
            self.second = int(second)

    @jsonrpc(pair=Pair, result=str)
    async def concat(pair):
        return str(pair.first) + str(pair.second)

    mfp = jsonrpc._route_post('fp')
    mfmp = jsonrpc._route_post('fmp')
    mfpk = jsonrpc._route_post('fpk')
    mfmpk = jsonrpc._route_post('fmpk')
    mfr = jsonrpc._route_post('fr')
    mfmr = jsonrpc._route_post('fmr')
    mfrk = jsonrpc._route_post('frk')
    mfmrk = jsonrpc._route_post('fmrk')
    mfab = jsonrpc._route_post('fab')
    mconcat = jsonrpc._route_post('concat')

    assert mfp.func is fp
    assert mfp.params == {'a': int}
    assert mfp.result is None

    assert mfmp.func is fmp
    assert mfmp.params == {'a': int}
    assert mfmp.result is None

    assert mfpk.func is fpk
    assert mfpk.params == {'a': int}
    assert mfpk.result is None

    assert mfmpk.func is fmpk
    assert mfmpk.params == {'a': int}
    assert mfmpk.result is None

    assert mfr.func is fr
    assert mfr.params is None
    assert mfr.result is str

    assert mfmr.func is fmr
    assert mfmr.params is None
    assert mfmr.result is str

    assert mfrk.func is frk
    assert mfrk.params is None
    assert mfrk.result is str

    assert mfmrk.func is fmrk
    assert mfmrk.params is None
    assert mfmrk.result is str

    assert mfab.func is fab
    assert mfab.params == {'a': int, 'b': int}

    assert mconcat.func is concat
    assert mconcat.params == {'pair': Pair}


# noinspection PyProtectedMember,DuplicatedCode
def test_params_result_override():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc(None, a=int)
    def fp(a: float):
        return str(a)

    @jsonrpc.method(None, a=int)
    def fmp(a: float):
        return str(a)

    @jsonrpc(a=int)
    def fpk(a: float):
        return str(a)

    @jsonrpc.method(a=int)
    def fmpk(a: float):
        return str(a)

    @jsonrpc(None, result=int)
    def fr(a) -> str:
        return str(a)

    @jsonrpc.method(None, result=int)
    def fmr(a) -> str:
        return str(a)

    @jsonrpc(result=int)
    def frk(a) -> str:
        return str(a)

    @jsonrpc.method(result=int)
    def fmrk(a) -> str:
        return str(a)

    mfp = jsonrpc._route_post('fp')
    mfmp = jsonrpc._route_post('fmp')
    mfpk = jsonrpc._route_post('fpk')
    mfmpk = jsonrpc._route_post('fmpk')
    mfr = jsonrpc._route_post('fr')
    mfmr = jsonrpc._route_post('fmr')
    mfrk = jsonrpc._route_post('frk')
    mfmrk = jsonrpc._route_post('fmrk')

    assert mfp.func is fp
    assert mfp.params == {'a': int}
    assert mfp.result is None

    assert mfmp.func is fmp
    assert mfmp.params == {'a': int}
    assert mfmp.result is None

    assert mfpk.func is fpk
    assert mfpk.params == {'a': int}
    assert mfpk.result is None

    assert mfmpk.func is fmpk
    assert mfmpk.params == {'a': int}
    assert mfmpk.result is None

    assert mfr.func is fr
    assert mfr.params is None
    assert mfr.result is int

    assert mfmr.func is fmr
    assert mfmr.params is None
    assert mfmr.result is int

    assert mfrk.func is frk
    assert mfrk.params is None
    assert mfrk.result is int

    assert mfmrk.func is fmrk
    assert mfmrk.params is None
    assert mfmrk.result is int


# noinspection PyProtectedMember
def test_rest_ws():
    # noinspection PyTypeChecker
    jsonrpc = Jsonrpc(None)

    @jsonrpc
    def fa():
        ...

    @jsonrpc()
    def fba():
        ...

    @jsonrpc.method
    def fma():
        ...

    @jsonrpc.method()
    def fmba():
        ...

    @jsonrpc.post
    def fp():
        ...

    @jsonrpc.post()
    def fpb():
        ...

    @jsonrpc.ws
    def fw():
        ...

    @jsonrpc.ws()
    def fwb():
        ...

    assert jsonrpc._route_post('fa') is not None
    assert jsonrpc._route_ws('fa') is not None

    assert jsonrpc._route_post('fba') is not None
    assert jsonrpc._route_ws('fba') is not None

    assert jsonrpc._route_post('fma') is not None
    assert jsonrpc._route_ws('fma') is not None

    assert jsonrpc._route_post('fmba') is not None
    assert jsonrpc._route_ws('fmba') is not None

    assert jsonrpc._route_post('fp') is not None
    assert jsonrpc._route_ws('fp') is None

    assert jsonrpc._route_post('fpb') is not None
    assert jsonrpc._route_ws('fpb') is None

    assert jsonrpc._route_post('fw') is None
    assert jsonrpc._route_ws('fw') is not None

    assert jsonrpc._route_post('fwb') is None
    assert jsonrpc._route_ws('fwb') is not None
