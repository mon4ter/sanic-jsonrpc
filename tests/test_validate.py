from pytest import fixture, mark
from sanic import Sanic

from sanic_jsonrpc import Jsonrpc


class Pair:
    def __init__(self, first: int, second: int):
        self.first = int(first)
        self.second = int(second)


@fixture
def app():
    app_ = Sanic()
    jsonrpc = Jsonrpc(app_, '/post')

    @jsonrpc
    def add(*terms: int) -> int:
        return sum(terms)

    @jsonrpc
    def to_pair(number: int) -> Pair:
        # noinspection PyTypeChecker
        return number // 10, number % 10

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app))


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
    {'jsonrpc': '2.0', 'method': 'to_pair', 'params': [35], 'id': 3},
    {'jsonrpc': '2.0', 'result': {'first': 3, 'second': 5}, 'id': 3}
)])
async def test_result(test_cli, in_: dict, out: dict):
    response = await test_cli.post('/post', json=in_)
    assert await response.json() == out
