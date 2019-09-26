from asyncio import sleep

from pytest import fixture, mark
from sanic import Sanic

from sanic_jsonrpc import Error, Jsonrpc


@fixture
def app():
    app_ = Sanic()
    jsonrpc = Jsonrpc(app_, '/post', '/ws')

    @jsonrpc
    async def awaitable():
        await sleep(0.01)
        return 'awaitable'

    @jsonrpc
    def return_error():
        return Error(-11111, "The Error")

    @jsonrpc
    def raise_error():
        raise Error(-12345, "Some error")

    @jsonrpc
    def invalid_params(a):
        return 'invalid_params({})'.format(a)

    @jsonrpc
    def raise_exception():
        return {}['1']

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'awaitable', 'id': 1},
    {'jsonrpc': '2.0', 'result': 'awaitable', 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'return_error', 'id': 2},
    {'jsonrpc': '2.0', 'error': {'code': -11111, 'message': "The Error"}, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'raise_error', 'id': 3},
    {'jsonrpc': '2.0', 'error': {'code': -12345, 'message': "Some error"}, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'invalid_params', 'id': 4},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'raise_exception', 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': "Internal error"}, 'id': 5}
)])
async def test_call(test_cli, in_: dict, out: dict):
    response = await test_cli.post('/post', json=in_)
    data = await response.json()
    assert data == out
