from asyncio import iscoroutine, wait_for
from json import dumps, loads
from logging import DEBUG

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol

from sanic_jsonrpc import SanicJsonrpc

Sanic.test_mode = True


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

    @jsonrpc
    def default():
        return 'default'

    @jsonrpc('Default')
    def default_cap():
        return 'Default'

    @jsonrpc.post
    def post():
        return 'post'

    @jsonrpc.post('Post')
    def post_cap():
        return 'Post'

    @jsonrpc.ws
    def ws():
        return 'ws'

    @jsonrpc.ws('Ws')
    def ws_cap():
        return 'Ws'

    @jsonrpc.request
    def request():
        return 'request'

    @jsonrpc.request('Request')
    def request_cap():
        return 'Request'

    @jsonrpc.notification
    def notification():
        return 'notification'

    @jsonrpc.notification('Notification')
    def notification_cap():
        return 'Notification'

    @jsonrpc.post_request
    def post_request():
        return 'post_request'

    @jsonrpc.post_request('PostRequest')
    def post_request_cap():
        return 'PostRequest'

    @jsonrpc.ws_request
    def ws_request():
        return 'ws_request'

    @jsonrpc.ws_request('WsRequest')
    def ws_request_cap():
        return 'WsRequest'

    @jsonrpc.post_notification
    def post_notification():
        return 'post_notification'

    @jsonrpc.post_notification('PostNotification')
    def post_notification_cap():
        return 'PostNotification'

    @jsonrpc.ws_notification
    def ws_notification():
        return 'ws_notification'

    @jsonrpc.ws_notification('WsNotification')
    def ws_notification_cap():
        return 'WsNotification'

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app))


@fixture
def test_cli_ws(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, scheme='ws', protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'default', 'id': 1},
    {'jsonrpc': '2.0', 'result': 'default', 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'Default', 'id': 2},
    {'jsonrpc': '2.0', 'result': 'Default', 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'post', 'id': 3},
    {'jsonrpc': '2.0', 'result': 'post', 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'Post', 'id': 4},
    {'jsonrpc': '2.0', 'result': 'Post', 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'ws', 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 5}
), (
    {'jsonrpc': '2.0', 'method': 'Ws', 'id': 6},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'request', 'id': 7},
    {'jsonrpc': '2.0', 'result': 'request', 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'Request', 'id': 8},
    {'jsonrpc': '2.0', 'result': 'Request', 'id': 8}
), (
    {'jsonrpc': '2.0', 'method': 'notification', 'id': 9},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 9}
), (
    {'jsonrpc': '2.0', 'method': 'Notification', 'id': 10},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 10}
), (
    {'jsonrpc': '2.0', 'method': 'post_request', 'id': 11},
    {'jsonrpc': '2.0', 'result': 'post_request', 'id': 11}
), (
    {'jsonrpc': '2.0', 'method': 'PostRequest', 'id': 12},
    {'jsonrpc': '2.0', 'result': 'PostRequest', 'id': 12}
), (
    {'jsonrpc': '2.0', 'method': 'ws_request', 'id': 13},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 13}
), (
    {'jsonrpc': '2.0', 'method': 'WsRequest', 'id': 14},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 14}
), (
    {'jsonrpc': '2.0', 'method': 'post_notification', 'id': 15},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 15}
), (
    {'jsonrpc': '2.0', 'method': 'PostNotification', 'id': 16},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 16}
), (
    {'jsonrpc': '2.0', 'method': 'ws_notification', 'id': 17},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 17}
), (
    {'jsonrpc': '2.0', 'method': 'WsNotification', 'id': 18},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 18}
)])
async def test_post_request(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    data = response.json()
    data = (await data) if iscoroutine(data) else data
    assert data == out


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'default', 'id': 1},
    {'jsonrpc': '2.0', 'result': 'default', 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'Default', 'id': 2},
    {'jsonrpc': '2.0', 'result': 'Default', 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'post', 'id': 3},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'Post', 'id': 4},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'ws', 'id': 5},
    {'jsonrpc': '2.0', 'result': 'ws', 'id': 5}
), (
    {'jsonrpc': '2.0', 'method': 'Ws', 'id': 6},
    {'jsonrpc': '2.0', 'result': 'Ws', 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'request', 'id': 7},
    {'jsonrpc': '2.0', 'result': 'request', 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'Request', 'id': 8},
    {'jsonrpc': '2.0', 'result': 'Request', 'id': 8}
), (
    {'jsonrpc': '2.0', 'method': 'notification', 'id': 9},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 9}
), (
    {'jsonrpc': '2.0', 'method': 'Notification', 'id': 10},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 10}
), (
    {'jsonrpc': '2.0', 'method': 'post_request', 'id': 11},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 11}
), (
    {'jsonrpc': '2.0', 'method': 'PostRequest', 'id': 12},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 12}
), (
    {'jsonrpc': '2.0', 'method': 'ws_request', 'id': 13},
    {'jsonrpc': '2.0', 'result': 'ws_request', 'id': 13}
), (
    {'jsonrpc': '2.0', 'method': 'WsRequest', 'id': 14},
    {'jsonrpc': '2.0', 'result': 'WsRequest', 'id': 14}
), (
    {'jsonrpc': '2.0', 'method': 'post_notification', 'id': 15},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 15}
), (
    {'jsonrpc': '2.0', 'method': 'PostNotification', 'id': 16},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 16}
), (
    {'jsonrpc': '2.0', 'method': 'ws_notification', 'id': 17},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 17}
), (
    {'jsonrpc': '2.0', 'method': 'WsNotification', 'id': 18},
    {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': "Method not found"}, 'id': 18}
)])
async def test_ws_request(caplog, test_cli_ws, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    ws = await test_cli_ws.ws_connect('/ws')
    await ws.send(dumps(in_))
    data = loads(await wait_for(ws.recv(), 0.01))
    await ws.close()
    await test_cli_ws.close()

    assert data == out
