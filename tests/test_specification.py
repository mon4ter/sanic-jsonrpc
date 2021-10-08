from asyncio import TimeoutError, iscoroutine, wait_for
from functools import partial
from http import HTTPStatus
from logging import DEBUG
from operator import contains
from typing import List

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from ujson import loads

from sanic_jsonrpc import SanicJsonrpc

Sanic.test_mode = True


def lists_equal_unordered(self: list, other: list) -> bool:
    return all(map(partial(contains, other), self)) and all(map(partial(contains, self), other))


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

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
    return loop.run_until_complete(sanic_client(app))


@fixture
def test_cli_ws(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, scheme='ws', protocol=WebSocketProtocol))


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
    None
), (
    '{"jsonrpc": "2.0", "method": "foobar"}',
    None
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
    None
)])
async def test_post(caplog, test_cli, in_: str, out: str):
    caplog.set_level(DEBUG)
    try:
        response = await test_cli.post('/post', content=in_)
    except TypeError:
        response = await test_cli.post('/post', data=in_)

    if (response.status_code if hasattr(response, 'status_code') else response.status) == HTTPStatus.MULTI_STATUS:
        left = response.json()
        left = (await left) if iscoroutine(left) else left

        if not isinstance(left, list):
            left = [left]

        right = loads(out)

        if not isinstance(right, list):
            right = [right]

        assert lists_equal_unordered(left, right)
    else:
        assert out is None


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
async def test_ws(caplog, test_cli_ws, in_: List[str], out: List[str]):
    caplog.set_level(DEBUG)
    ws = await test_cli_ws.ws_connect('/ws')

    for data in in_:
        await ws.send(data) if hasattr(ws, 'send') else await ws.send_str(data)

    left = []

    while True:
        try:
            left.append(
                loads(await wait_for(ws.recv(), 0.1)) if hasattr(ws, 'recv') else await ws.receive_json(timeout=0.1)
            )
        except TimeoutError:
            break

    await ws.close()
    await test_cli_ws.close()

    right = [loads(s) for s in out]

    assert lists_equal_unordered(left, right)
