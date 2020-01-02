from logging import DEBUG
from typing import Tuple

from pytest import fixture, mark
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.websocket import WebSocketProtocol
from websockets import WebSocketCommonProtocol

from sanic_jsonrpc import Jsonrpc, Notifier, Request


class Pair:
    def __init__(self, first: int, second: int):
        self.first = int(first)
        self.second = int(second)


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = Jsonrpc(app_, '/post', '/ws')

    @jsonrpc
    def add(*terms: int) -> int:
        return sum(terms)

    @jsonrpc(result=Pair)
    def to_pair(number: int) -> Tuple[int, int]:
        return number // 10, number % 10

    @jsonrpc(result=int)
    def invalid_response(s: int) -> str:
        return 's{}'.format(s)

    @jsonrpc
    def sanic_request(req: SanicRequest) -> bool:
        return isinstance(req, SanicRequest)

    @jsonrpc.request
    def request(req: Request) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def app(app__: Sanic) -> bool:
        return app__ is app_

    @jsonrpc.post
    def ws(ws_: WebSocketCommonProtocol) -> bool:
        return ws_ is None

    @jsonrpc.ws
    def ws(ws_: WebSocketCommonProtocol) -> bool:
        print(type(ws_))
        return isinstance(ws_, WebSocketCommonProtocol)

    @jsonrpc.post
    def notifier(n: Notifier) -> bool:
        return n is None

    @jsonrpc.ws
    def notifier(n: Notifier) -> bool:
        return n.__qualname__ == 'Jsonrpc._notifier.<locals>.notifier'

    @jsonrpc
    def multi_word(word: str, multi: int) -> str:
        return word * multi

    @jsonrpc
    def sum_two_pairs(p1: Pair, p2: Pair) -> Pair:
        return Pair(p1.first + p2.first, p1.second + p2.second)

    @jsonrpc
    def sum_pairs(*pairs: Pair) -> Pair:
        return Pair(sum(p.first for p in pairs), sum(p.second for p in pairs))

    @jsonrpc
    def fancy_string(**kwargs: str) -> str:
        return ';'.join('{}={}'.format(k, kwargs[k]) for k in sorted(kwargs))

    @jsonrpc
    def arg_request(arg: int, req: Request) -> int:
        return arg + req.id

    @jsonrpc
    def args_varargs_special(first: str, in_: Request, *args: str, app__: Sanic, **kwargs: str) -> bool:
        return (
            isinstance(first, str) and
            isinstance(in_, Request) and
            all(isinstance(a, str) for a in args) and
            app__ is app_ and
            all(isinstance(k, str) for k in kwargs)
        )

    @jsonrpc
    def recover(pair: Pair) -> int:
        return pair.first + pair.second

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'add', 'params': [1, 2, 3], 'id': 1},
    {'jsonrpc': '2.0', 'result': 6, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'add', 'params': [3.0, 4.0, 5.0], 'id': 2},
    {'jsonrpc': '2.0', 'result': 12, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'add', 'params': [3.1, 4.1, 5.1], 'id': 3},
    {'jsonrpc': '2.0', 'result': 12, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'to_pair', 'params': [35], 'id': 4},
    {'jsonrpc': '2.0', 'result': {'first': 3, 'second': 5}, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'invalid_response', 'params': [12], 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': "Internal error"}, 'id': 5}
), (
    {'jsonrpc': '2.0', 'method': 'sanic_request', 'id': 6},
    {'jsonrpc': '2.0', 'result': True, 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'request', 'id': 7},
    {'jsonrpc': '2.0', 'result': True, 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'ws', 'id': 8},
    {'jsonrpc': '2.0', 'result': True, 'id': 8}
), (
    {'jsonrpc': '2.0', 'method': 'notifier', 'id': 9},
    {'jsonrpc': '2.0', 'result': True, 'id': 9}
), (
    {'jsonrpc': '2.0', 'method': 'app', 'id': 10},
    {'jsonrpc': '2.0', 'result': True, 'id': 10}
), (
    {'jsonrpc': '2.1', 'method': 'app', 'id': 11},
    {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': "Invalid Request"}, 'id': None}
), (
    {'jsonrpc': '2.0', 'method': 'add', 'params': ['1', '2', '3'], 'id': 12},
    {'jsonrpc': '2.0', 'result': 6, 'id': 12}
), (
    {'jsonrpc': '2.0', 'method': 'multi_word', 'params': ['a', '3'], 'id': 13},
    {'jsonrpc': '2.0', 'result': 'aaa', 'id': 13}
), (
    {'jsonrpc': '2.0', 'method': 'multi_word', 'params': [5, 5], 'id': 15},
    {'jsonrpc': '2.0', 'result': '55555', 'id': 15}
), (
    {'jsonrpc': '2.0', 'method': 'add', 'params': ['1', '2', 'three'], 'id': 16},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 16}
), (
    {'jsonrpc': '2.0', 'method': 'to_pair', 'params': ['one'], 'id': 17},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 17}
), (
    {'jsonrpc': '2.0', 'method': 'to_pair', 'params': [1, 2], 'id': 18},
    {'jsonrpc': '2.0', 'result': {'first': 0, 'second': 1}, 'id': 18}
), (
    {'jsonrpc': '2.0', 'method': 'sum_two_pairs', 'params': [[1, 2], [10, 20]], 'id': 19},
    {'jsonrpc': '2.0', 'result': {'first': 11, 'second': 22}, 'id': 19}
), (
    {'jsonrpc': '2.0', 'method': 'sum_two_pairs', 'params': [
        {'first': 3, 'second': 4}, {'first': 30, 'second': 40}
    ], 'id': 20},
    {'jsonrpc': '2.0', 'result': {'first': 33, 'second': 44}, 'id': 20}
), (
    {'jsonrpc': '2.0', 'method': 'sum_pairs', 'params': [[1, 2], [10, 20]], 'id': 21},
    {'jsonrpc': '2.0', 'result': {'first': 11, 'second': 22}, 'id': 21}
), (
    {'jsonrpc': '2.0', 'method': 'sum_pairs', 'params': [
        {'first': 3, 'second': 4}, {'first': 30, 'second': 40}
    ], 'id': 22},
    {'jsonrpc': '2.0', 'result': {'first': 33, 'second': 44}, 'id': 22}
), (
    {'jsonrpc': '2.0', 'method': 'sum_pairs', 'params': [[6, 7]], 'id': 23},
    {'jsonrpc': '2.0', 'result': {'first': 6, 'second': 7}, 'id': 23}
), (
    {'jsonrpc': '2.0', 'method': 'sum_pairs', 'params': [], 'id': 24},
    {'jsonrpc': '2.0', 'result': {'first': 0, 'second': 0}, 'id': 24}
), (
    {'jsonrpc': '2.0', 'method': 'fancy_string', 'params': {'foo': 123, 'bar': 456}, 'id': 24},
    {'jsonrpc': '2.0', 'result': 'bar=456;foo=123', 'id': 24}
), (
    {'jsonrpc': '2.0', 'method': 'arg_request', 'params': '700', 'id': 25},
    {'jsonrpc': '2.0', 'result': 725, 'id': 25}
), (
    {'jsonrpc': '2.0', 'method': 'args_varargs_special', 'params': [0, 1, 10, 20], 'id': 25},
    {'jsonrpc': '2.0', 'result': True, 'id': 25}
), (
    {'jsonrpc': '2.0', 'method': 'args_varargs_special', 'params': {
        'first': 0, 'a': 123, 'b': 456, 'c': 789
    }, 'id': 26},
    {'jsonrpc': '2.0', 'result': True, 'id': 26}
), (
    {'jsonrpc': '2.0', 'method': 'recover', 'params': [7, 4], 'id': 27},
    {'jsonrpc': '2.0', 'result': 11, 'id': 27}
), (
    {'jsonrpc': '2.0', 'method': 'recover', 'params': {'first': 8, 'second': 9}, 'id': 28},
    {'jsonrpc': '2.0', 'result': 17, 'id': 28}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    assert await response.json() == out


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'ws', 'id': 1},
    {'jsonrpc': '2.0', 'result': True, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'notifier', 'id': 2},
    {'jsonrpc': '2.0', 'result': True, 'id': 2}
)])
async def test_ws(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    ws = await test_cli.ws_connect('/ws')
    await ws.send_json(in_)
    data = await ws.receive_json(timeout=0.01)
    await ws.close()

    assert data == out
