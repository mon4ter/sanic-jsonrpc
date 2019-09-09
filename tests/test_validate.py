from typing import Tuple

from pytest import fixture, mark
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.websocket import WebSocketCommonProtocol, WebSocketProtocol

from sanic_jsonrpc import Jsonrpc, Notifier, Request


class Pair:
    def __init__(self, first: int, second: int):
        self.first = int(first)
        self.second = int(second)


@fixture
def app():
    app_ = Sanic()
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
    def sanic_request(req: SanicRequest):
        return isinstance(req, SanicRequest)

    @jsonrpc.request
    def request(req: Request):
        return isinstance(req, Request)

    @jsonrpc
    def app(app__: Sanic):
        return app__ is app_

    @jsonrpc.post
    def ws(ws_: WebSocketCommonProtocol):
        return ws_ is None

    @jsonrpc.ws
    def ws(ws_: WebSocketCommonProtocol):
        return isinstance(ws_, WebSocketCommonProtocol)

    @jsonrpc.post
    def notifier(n: Notifier):
        return n is None

    @jsonrpc.ws
    def notifier(n: Notifier):
        return n.__qualname__ == 'Jsonrpc._notifier.<locals>.notifier'

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
    {'jsonrpc': '2.0', 'method': 'sanic_request', 'params': [], 'id': 6},
    {'jsonrpc': '2.0', 'result': True, 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'request', 'params': [], 'id': 7},
    {'jsonrpc': '2.0', 'result': True, 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'ws', 'params': [], 'id': 8},
    {'jsonrpc': '2.0', 'result': True, 'id': 8}
), (
    {'jsonrpc': '2.0', 'method': 'notifier', 'params': [], 'id': 9},
    {'jsonrpc': '2.0', 'result': True, 'id': 9}
), (
    {'jsonrpc': '2.0', 'method': 'app', 'params': [], 'id': 10},
    {'jsonrpc': '2.0', 'result': True, 'id': 10}
)])
async def test_post(test_cli, in_: dict, out: dict):
    response = await test_cli.post('/post', json=in_)
    assert await response.json() == out


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'ws', 'params': [], 'id': 1},
    {'jsonrpc': '2.0', 'result': True, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'notifier', 'params': [], 'id': 2},
    {'jsonrpc': '2.0', 'result': True, 'id': 2}
)])
async def test_ws(test_cli, in_: dict, out: dict):
    ws = await test_cli.ws_connect('/ws')
    await ws.send_json(in_)
    data = await ws.receive_json(timeout=0.01)
    assert data == out
