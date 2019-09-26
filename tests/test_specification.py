from asyncio import TimeoutError
from functools import partial
from operator import contains
from typing import List

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from ujson import loads

from sanic_jsonrpc import Jsonrpc


def lists_equal_unordered(self: list, other: list) -> bool:
    return all(map(partial(contains, other), self)) and all(map(partial(contains, self), other))


@fixture
def app():
    app_ = Sanic()
    jsonrpc = Jsonrpc(app_, '/post', '/ws')

    @jsonrpc
    def subtract(minuend: int, subtrahend: int) -> int:
        return minuend - subtrahend

    @jsonrpc('sum')
    def add(*terms: int) -> int:
        return sum(terms)

    @jsonrpc
    def get_data():
        return ['hello', 5]

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    '{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}',
    '{"jsonrpc": "2.0", "result": 19, "id": 1}'
), (
    '{"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}',
    '{"jsonrpc": "2.0", "result": -19, "id": 2}'
), (
    '{"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 3}',
    '{"jsonrpc": "2.0", "result": 19, "id": 3}'
), (
    '{"jsonrpc": "2.0", "method": "subtract", "params": {"minuend": 42, "subtrahend": 23}, "id": 4}',
    '{"jsonrpc": "2.0", "result": 19, "id": 4}'
), (
    '{"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]}',
    ''
), (
    '{"jsonrpc": "2.0", "method": "foobar"}',
    ''
), (
    '{"jsonrpc": "2.0", "method": "foobar", "id": "1"}',
    '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "1"}'
), (
    '{"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]',
    '{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}'
), (
    '{"jsonrpc": "2.0", "method": 1, "params": "bar"}',
    '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'
), (
    '['
    '    {"jsonrpc": "2.0", "method": "sum", "params":[1, 2, 4], "id": "1"},'
    '    {"jsonrpc": "2.0", "method"'
    ']',
    '{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}'
), (
    '[]',
    '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'
), (
    '[1]',
    '['
    '    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'
    ']'
), (
    '[1,2,3]',
    '['
    '    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},'
    '    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},'
    '    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'
    ']'
), (
    '['
    '    {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},'
    '    {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},'
    '    {"jsonrpc": "2.0", "method": "subtract", "params": [42,23], "id": "2"},'
    '    {"foo": "boo"},'
    '    {"jsonrpc": "2.0", "method": "foo.get", "params": {"name": "myself"}, "id": "5"},'
    '    {"jsonrpc": "2.0", "method": "get_data", "id": "9"}'
    ']',
    '['
    '    {"jsonrpc": "2.0", "result": 7, "id": "1"},'
    '    {"jsonrpc": "2.0", "result": 19, "id": "2"},'
    '    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},'
    '    {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "5"},'
    '    {"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"}'
    ']'
), (
    '['
    '    {"jsonrpc": "2.0", "method": "notify_sum", "params": [1,2,4]},'
    '    {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]}'
    ']',
    ''
)])
async def test_post(test_cli, in_: str, out: str):
    response = await test_cli.post('/post', data=in_)

    if response.headers['content-type'] == 'application/json':
        left = await response.json()

        if not isinstance(left, list):
            left = [left]

        right = loads(out)

        if not isinstance(right, list):
            right = [right]

        assert lists_equal_unordered(left, right)
    else:
        assert await response.text() == out


@mark.parametrize('in_,out', [(
    ['{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}'],
    ['{"jsonrpc": "2.0", "result": 19, "id": 1}']
), (
    ['{"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}'],
    ['{"jsonrpc": "2.0", "result": -19, "id": 2}']
), (
    ['{"jsonrpc": "2.0", "method": "subtract", "params": {"subtrahend": 23, "minuend": 42}, "id": 3}'],
    ['{"jsonrpc": "2.0", "result": 19, "id": 3}']
), (
    ['{"jsonrpc": "2.0", "method": "subtract", "params": {"minuend": 42, "subtrahend": 23}, "id": 4}'],
    ['{"jsonrpc": "2.0", "result": 19, "id": 4}']
), (
    ['{"jsonrpc": "2.0", "method": "update", "params": [1,2,3,4,5]}'],
    []
), (
    ['{"jsonrpc": "2.0", "method": "foobar"}'],
    []
), (
    ['{"jsonrpc": "2.0", "method": "foobar", "id": "1"}'],
    ['{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "1"}']
), (
    ['{"jsonrpc": "2.0", "method": "foobar, "params": "bar", "baz]'],
    ['{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}']
), (
    ['{"jsonrpc": "2.0", "method": 1, "params": "bar"}'],
    ['{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}']
), (
    [
        '{"jsonrpc": "2.0", "method": "sum", "params":[1, 2, 4], "id": "1"}',
        '{"jsonrpc": "2.0", "method"'
    ],
    [
        '{"jsonrpc": "2.0", "result": 7, "id": "1"}',
        '{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}'
    ]
), (
    ['[]'],
    ['{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}']
), (
    ['1'],
    ['{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}']
), (
    ['1', '2', '3'],
    [
        '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
        '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
        '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'
    ]
), (
    [
        '{"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"}',
        '{"jsonrpc": "2.0", "method": "notify_hello", "params": [7]}',
        '{"jsonrpc": "2.0", "method": "subtract", "params": [42,23], "id": "2"}',
        '{"foo": "boo"}',
        '{"jsonrpc": "2.0", "method": "foo.get", "params": {"name": "myself"}, "id": "5"}',
        '{"jsonrpc": "2.0", "method": "get_data", "id": "9"}'
    ],
    [
        '{"jsonrpc": "2.0", "result": 7, "id": "1"}',
        '{"jsonrpc": "2.0", "result": 19, "id": "2"}',
        '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
        '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "5"}',
        '{"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"}'
    ]
), (
    [
        '{"jsonrpc": "2.0", "method": "notify_sum", "params": [1,2,4]}',
        '{"jsonrpc": "2.0", "method": "notify_hello", "params": [7]}'
    ],
    []
)])
async def test_ws(test_cli, in_: List[str], out: List[str]):
    ws = await test_cli.ws_connect('/ws')

    for data in in_:
        await ws.send_str(data)

    left = []

    while True:
        try:
            left.append(loads(await ws.receive_str(timeout=0.01)))
        except TimeoutError:
            await ws.close()
            break

    right = [loads(s) for s in out]
    assert lists_equal_unordered(left, right)
