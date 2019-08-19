from functools import partial
from operator import contains

from pytest import fixture, mark
from sanic import Sanic
from sanic.request import Request
from ujson import loads

from sanic_jsonrpc import Jsonrpc


@fixture
def jsonrpc_fixture():
    app = Sanic()
    jsonrpc = Jsonrpc(app, '/post')

    @jsonrpc
    def subtract(minuend: int, subtrahend: int) -> int:
        return minuend - subtrahend

    @jsonrpc('sum')
    def add(*terms: int) -> int:
        return sum(terms)

    @jsonrpc
    def get_data():
        return ['hello', 5]

    yield jsonrpc


@mark.asyncio
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
    b''
), (
    '{"jsonrpc": "2.0", "method": "foobar"}',
    b''
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
    b''
)])
async def test_specification(jsonrpc_fixture, in_, out):
    request = Request(None, None, None, None, None)
    request.body_push(in_.encode())
    request.body_finish()
    # noinspection PyProtectedMember
    response = await jsonrpc_fixture._post(request)

    if response.body:
        left = loads(response.body)

        if not isinstance(left, list):
            left = [left]

        right = loads(out)

        if not isinstance(right, list):
            right = [right]

        assert all(map(partial(contains, right), left)) and all(map(partial(contains, left), right))
    else:
        assert response.body == out
