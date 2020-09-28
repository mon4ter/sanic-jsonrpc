from logging import DEBUG
from typing import Optional

from fashionable import Attribute, Model
from pytest import fixture, mark
from sanic import Sanic
from sanic.request import Request as SanicRequest
from sanic.websocket import WebSocketProtocol
from websockets import WebSocketCommonProtocol as WebSocket

from sanic_jsonrpc import Incoming, Notification, Notifier, Request, SanicJsonrpc


class Pair:
    def __init__(self, first: int, second: int):
        self.first = int(first)
        self.second = int(second)

    def __iter__(self):
        yield 'first', self.first
        yield 'second', self.second


class C(Model):
    x = Attribute(float)
    y = Attribute(float)


class Params(Model):
    a = Attribute(str)
    b = Attribute(Optional[int])
    c = Attribute(C)


class DefaultParams(Model):
    a = Attribute(str, default='a')
    b = Attribute(int, default=0)
    c = Attribute(C, default=C(0, 0))


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

    @jsonrpc
    def vararg(*terms: int) -> int:
        return sum(terms)

    @jsonrpc(result=dict)
    def result(number: int) -> Pair:
        return Pair(number // 10, number % 10)

    @jsonrpc(result=int)
    def invalid_response(s: int) -> str:
        return 's{}'.format(s)

    @jsonrpc
    def sanic_request_positional(req: SanicRequest) -> bool:
        return isinstance(req, SanicRequest)

    @jsonrpc
    def sanic_request_keyword(*, req: SanicRequest) -> bool:
        return isinstance(req, SanicRequest)

    @jsonrpc
    def app_positional(app__: Sanic) -> bool:
        return app__ is app_

    @jsonrpc
    def app_keyword(*, app__: Sanic) -> bool:
        return app__ is app_

    @jsonrpc
    def request_positional(req: Request) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def request_keyword(*, req: Request) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def optional_request_positional(req: Optional[Request]) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def optional_request_keyword(*, req: Optional[Request]) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def incoming_positional(req: Incoming) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def incoming_keyword(*, req: Incoming) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def optional_incoming_positional(req: Optional[Incoming]) -> bool:
        return isinstance(req, Request)

    @jsonrpc
    def optional_incoming_keyword(*, req: Optional[Incoming]) -> bool:
        return isinstance(req, Request)

    @jsonrpc.post
    def ws_positional(ws_: WebSocket) -> bool:
        return ws_ is None

    @jsonrpc.ws
    def ws_positional(ws_: WebSocket) -> bool:
        return isinstance(ws_, WebSocket)

    @jsonrpc.post
    def ws_keyword(*, ws_: WebSocket) -> bool:
        return ws_ is None

    @jsonrpc.ws
    def ws_keyword(*, ws_: WebSocket) -> bool:
        return isinstance(ws_, WebSocket)

    @jsonrpc.post
    def optional_ws_positional(ws_: Optional[WebSocket]) -> bool:
        return ws_ is None

    @jsonrpc.ws
    def optional_ws_positional(ws_: Optional[WebSocket]) -> bool:
        return isinstance(ws_, WebSocket)

    @jsonrpc.post
    def optional_ws_keyword(*, ws_: Optional[WebSocket]) -> bool:
        return ws_ is None

    @jsonrpc.ws
    def optional_ws_keyword(*, ws_: Optional[WebSocket]) -> bool:
        return isinstance(ws_, WebSocket)

    @jsonrpc.post
    def notifier_positional(n: Notifier) -> bool:
        return n is None

    @jsonrpc.ws
    def notifier_positional(n: Notifier) -> bool:
        return isinstance(n, Notifier)

    @jsonrpc.post
    def notifier_keyword(*, n: Notifier) -> bool:
        return n is None

    @jsonrpc.ws
    def notifier_keyword(*, n: Notifier) -> bool:
        return isinstance(n, Notifier)

    @jsonrpc.post
    def optional_notifier_positional(n: Optional[Notifier]) -> bool:
        return n is None

    @jsonrpc.ws
    def optional_notifier_positional(n: Optional[Notifier]) -> bool:
        return isinstance(n, Notifier)

    @jsonrpc.post
    def optional_notifier_keyword(*, n: Optional[Notifier]) -> bool:
        return n is None

    @jsonrpc.ws
    def optional_notifier_keyword(*, n: Optional[Notifier]) -> bool:
        return isinstance(n, Notifier)

    @jsonrpc
    def notification_positional(req: Notification) -> bool:
        return isinstance(req, Notification)

    @jsonrpc
    def notification_keyword(*, req: Notification) -> bool:
        return isinstance(req, Notification)

    @jsonrpc
    def optional_notification_positional(req: Optional[Notification]) -> bool:
        return isinstance(req, Notification)

    @jsonrpc
    def optional_notification_keyword(*, req: Optional[Notification]) -> bool:
        return isinstance(req, Notification)

    @jsonrpc
    def params_types(word: str, multi: int) -> str:
        return word * multi

    @jsonrpc(result=dict)
    def class_args(p1: Pair, p2: Pair) -> Pair:
        return Pair(p1.first + p2.first, p1.second + p2.second)

    @jsonrpc(result=dict)
    def class_vararg(*pairs: Pair) -> Pair:
        return Pair(sum(p.first for p in pairs), sum(p.second for p in pairs))

    @jsonrpc
    def varkw(**kwargs: str) -> str:
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

    @jsonrpc
    def default_arg(a: str, b: str = '-') -> str:
        return a + b

    @jsonrpc
    def default_kwarg(*, a: str, b: str = '-') -> str:
        return a + b

    @jsonrpc
    def recover_once(first: bool, second: bool) -> bool:
        return first and second

    @jsonrpc
    def model(params: Params) -> str:
        return repr(params)

    @jsonrpc
    def default_model(params: DefaultParams = DefaultParams()) -> str:
        return repr(params)

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'vararg', 'params': [1, 2, 3], 'id': 1},
    {'jsonrpc': '2.0', 'result': 6, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'vararg', 'params': [3.0, 4.0, 5.0], 'id': 2},
    {'jsonrpc': '2.0', 'result': 12, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'vararg', 'params': [3.1, 4.1, 5.1], 'id': 3},
    {'jsonrpc': '2.0', 'result': 12, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'result', 'params': [35], 'id': 4},
    {'jsonrpc': '2.0', 'result': {'first': 3, 'second': 5}, 'id': 4}
), (
    {'jsonrpc': '2.1', 'method': 'invalid_request', 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': "Invalid Request"}, 'id': None}
), (
    {'jsonrpc': '2.0', 'method': 'invalid_response', 'params': [12], 'id': 6},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': "Internal error"}, 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'sanic_request_positional', 'id': 7},
    {'jsonrpc': '2.0', 'result': True, 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'sanic_request_keyword', 'id': 8},
    {'jsonrpc': '2.0', 'result': True, 'id': 8}
), (
    {'jsonrpc': '2.0', 'method': 'app_positional', 'id': 9},
    {'jsonrpc': '2.0', 'result': True, 'id': 9}
), (
    {'jsonrpc': '2.0', 'method': 'app_keyword', 'id': 10},
    {'jsonrpc': '2.0', 'result': True, 'id': 10}
), (
    {'jsonrpc': '2.0', 'method': 'request_positional', 'id': 11},
    {'jsonrpc': '2.0', 'result': True, 'id': 11}
), (
    {'jsonrpc': '2.0', 'method': 'request_keyword', 'id': 12},
    {'jsonrpc': '2.0', 'result': True, 'id': 12}
), (
    {'jsonrpc': '2.0', 'method': 'optional_request_positional', 'id': 13},
    {'jsonrpc': '2.0', 'result': True, 'id': 13}
), (
    {'jsonrpc': '2.0', 'method': 'optional_request_keyword', 'id': 14},
    {'jsonrpc': '2.0', 'result': True, 'id': 14}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_positional', 'id': 15},
    {'jsonrpc': '2.0', 'result': True, 'id': 15}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_keyword', 'id': 16},
    {'jsonrpc': '2.0', 'result': True, 'id': 16}
), (
    {'jsonrpc': '2.0', 'method': 'optional_incoming_positional', 'id': 17},
    {'jsonrpc': '2.0', 'result': True, 'id': 17}
), (
    {'jsonrpc': '2.0', 'method': 'optional_incoming_keyword', 'id': 18},
    {'jsonrpc': '2.0', 'result': True, 'id': 18}
), (
    {'jsonrpc': '2.0', 'method': 'ws_positional', 'id': 19},
    {'jsonrpc': '2.0', 'result': True, 'id': 19}
), (
    {'jsonrpc': '2.0', 'method': 'ws_keyword', 'id': 20},
    {'jsonrpc': '2.0', 'result': True, 'id': 20}
), (
    {'jsonrpc': '2.0', 'method': 'optional_ws_positional', 'id': 21},
    {'jsonrpc': '2.0', 'result': True, 'id': 21}
), (
    {'jsonrpc': '2.0', 'method': 'optional_ws_keyword', 'id': 22},
    {'jsonrpc': '2.0', 'result': True, 'id': 22}
), (
    {'jsonrpc': '2.0', 'method': 'notifier_positional', 'id': 23},
    {'jsonrpc': '2.0', 'result': True, 'id': 23}
), (
    {'jsonrpc': '2.0', 'method': 'notifier_keyword', 'id': 24},
    {'jsonrpc': '2.0', 'result': True, 'id': 24}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notifier_positional', 'id': 25},
    {'jsonrpc': '2.0', 'result': True, 'id': 25}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notifier_keyword', 'id': 26},
    {'jsonrpc': '2.0', 'result': True, 'id': 26}
), (
    {'jsonrpc': '2.0', 'method': 'notification_positional', 'id': 27},
    {'jsonrpc': '2.0', 'result': False, 'id': 27}
), (
    {'jsonrpc': '2.0', 'method': 'notification_keyword', 'id': 28},
    {'jsonrpc': '2.0', 'result': False, 'id': 28}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notification_positional', 'id': 29},
    {'jsonrpc': '2.0', 'result': False, 'id': 29}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notification_keyword', 'id': 30},
    {'jsonrpc': '2.0', 'result': False, 'id': 30}
), (
    {'jsonrpc': '2.0', 'method': 'vararg', 'params': ['1', '2', '3'], 'id': 31},
    {'jsonrpc': '2.0', 'result': 6, 'id': 31}
), (
    {'jsonrpc': '2.0', 'method': 'params_types', 'params': ['a', '3'], 'id': 32},
    {'jsonrpc': '2.0', 'result': 'aaa', 'id': 32}
), (
    {'jsonrpc': '2.0', 'method': 'params_types', 'params': [5, 5], 'id': 33},
    {'jsonrpc': '2.0', 'result': '55555', 'id': 33}
), (
    {'jsonrpc': '2.0', 'method': 'vararg', 'params': ['1', '2', 'three'], 'id': 34},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 34}
), (
    {'jsonrpc': '2.0', 'method': 'result', 'params': ['one'], 'id': 35},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 35}
), (
    {'jsonrpc': '2.0', 'method': 'result', 'params': [1, 2], 'id': 36},
    {'jsonrpc': '2.0', 'result': {'first': 0, 'second': 1}, 'id': 36}
), (
    {'jsonrpc': '2.0', 'method': 'class_args', 'params': [[1, 2], [10, 20]], 'id': 37},
    {'jsonrpc': '2.0', 'result': {'first': 11, 'second': 22}, 'id': 37}
), (
    {'jsonrpc': '2.0', 'method': 'class_args', 'params': [
        {'first': 3, 'second': 4}, {'first': 30, 'second': 40}
    ], 'id': 38},
    {'jsonrpc': '2.0', 'result': {'first': 33, 'second': 44}, 'id': 38}
), (
    {'jsonrpc': '2.0', 'method': 'class_vararg', 'params': [[1, 2], [10, 20]], 'id': 39},
    {'jsonrpc': '2.0', 'result': {'first': 11, 'second': 22}, 'id': 39}
), (
    {'jsonrpc': '2.0', 'method': 'class_vararg', 'params': [
        {'first': 3, 'second': 4}, {'first': 30, 'second': 40}
    ], 'id': 40},
    {'jsonrpc': '2.0', 'result': {'first': 33, 'second': 44}, 'id': 40}
), (
    {'jsonrpc': '2.0', 'method': 'class_vararg', 'params': [[6, 7]], 'id': 41},
    {'jsonrpc': '2.0', 'result': {'first': 6, 'second': 7}, 'id': 41}
), (
    {'jsonrpc': '2.0', 'method': 'class_vararg', 'params': [], 'id': 42},
    {'jsonrpc': '2.0', 'result': {'first': 0, 'second': 0}, 'id': 42}
), (
    {'jsonrpc': '2.0', 'method': 'varkw', 'params': {'foo': 123, 'bar': 456}, 'id': 43},
    {'jsonrpc': '2.0', 'result': 'bar=456;foo=123', 'id': 43}
), (
    {'jsonrpc': '2.0', 'method': 'arg_request', 'params': '700', 'id': 44},
    {'jsonrpc': '2.0', 'result': 744, 'id': 44}
), (
    {'jsonrpc': '2.0', 'method': 'args_varargs_special', 'params': [0, 1, 10, 20], 'id': 45},
    {'jsonrpc': '2.0', 'result': True, 'id': 45}
), (
    {'jsonrpc': '2.0', 'method': 'args_varargs_special', 'params': {
        'first': 0, 'a': 123, 'b': 456, 'c': 789
    }, 'id': 46},
    {'jsonrpc': '2.0', 'result': True, 'id': 46}
), (
    {'jsonrpc': '2.0', 'method': 'recover', 'params': [7, 4], 'id': 47},
    {'jsonrpc': '2.0', 'result': 11, 'id': 47}
), (
    {'jsonrpc': '2.0', 'method': 'recover', 'params': {'first': 8, 'second': 9}, 'id': 48},
    {'jsonrpc': '2.0', 'result': 17, 'id': 48}
), (
    {'jsonrpc': '2.0', 'method': 'default_arg', 'params': [123, 456], 'id': 49},
    {'jsonrpc': '2.0', 'result': '123456', 'id': 49}
), (
    {'jsonrpc': '2.0', 'method': 'default_arg', 'params': [123], 'id': 50},
    {'jsonrpc': '2.0', 'result': '123-', 'id': 50}
), (
    {'jsonrpc': '2.0', 'method': 'default_kwarg', 'params': {'a': 123, 'b': 456}, 'id': 51},
    {'jsonrpc': '2.0', 'result': '123456', 'id': 51}
), (
    {'jsonrpc': '2.0', 'method': 'default_kwarg', 'params': {'a': 123}, 'id': 52},
    {'jsonrpc': '2.0', 'result': '123-', 'id': 52}
), (
    {'jsonrpc': '2.0', 'method': 'recover_once', 'params': [True, True], 'id': 53},
    {'jsonrpc': '2.0', 'result': True, 'id': 53}
), (
    {'jsonrpc': '2.0', 'method': 'recover_once', 'params': True, 'id': 54},
    {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': "Invalid params"}, 'id': 54}
), (
    {'jsonrpc': '2.0', 'method': 'model', 'params': [1, 2, [5, 6]], 'id': 55},
    {'jsonrpc': '2.0', 'result': "Params(a='1', b=2, c=C(x=5.0, y=6.0))", 'id': 55}
), (
    {'jsonrpc': '2.0', 'method': 'model', 'params': {'a': 1, 'c': {'x': 5, 'y': 6}}, 'id': 56},
    {'jsonrpc': '2.0', 'result': "Params(a='1', c=C(x=5.0, y=6.0))", 'id': 56}
), (
    {'jsonrpc': '2.0', 'method': 'default_model', 'params': [], 'id': 58},
    {'jsonrpc': '2.0', 'result': "DefaultParams(a='a', b=0, c=C(x=0.0, y=0.0))", 'id': 58}
), (
    {'jsonrpc': '2.0', 'method': 'default_model', 'params': {}, 'id': 59},
    {'jsonrpc': '2.0', 'result': "DefaultParams(a='a', b=0, c=C(x=0.0, y=0.0))", 'id': 59}
), (
    {'jsonrpc': '2.0', 'method': 'default_model', 'id': 60},
    {'jsonrpc': '2.0', 'result': "DefaultParams(a='a', b=0, c=C(x=0.0, y=0.0))", 'id': 60}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    assert await response.json() == out


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'ws_positional', 'id': 1},
    {'jsonrpc': '2.0', 'result': True, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'ws_keyword', 'id': 2},
    {'jsonrpc': '2.0', 'result': True, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'optional_ws_positional', 'id': 3},
    {'jsonrpc': '2.0', 'result': True, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'optional_ws_keyword', 'id': 4},
    {'jsonrpc': '2.0', 'result': True, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'notifier_positional', 'id': 5},
    {'jsonrpc': '2.0', 'result': True, 'id': 5}
), (
    {'jsonrpc': '2.0', 'method': 'notifier_keyword', 'id': 6},
    {'jsonrpc': '2.0', 'result': True, 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notifier_positional', 'id': 7},
    {'jsonrpc': '2.0', 'result': True, 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'optional_notifier_keyword', 'id': 8},
    {'jsonrpc': '2.0', 'result': True, 'id': 8}
)])
async def test_ws(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    ws = await test_cli.ws_connect('/ws')
    await ws.send_json(in_)
    data = await ws.receive_json(timeout=0.01)
    await ws.close()
    await test_cli.close()

    assert data == out
