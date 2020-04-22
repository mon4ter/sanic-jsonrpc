from logging import DEBUG
from typing import List, Optional

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol

from sanic_jsonrpc import Events, Incoming, Outgoing, Response, SanicJsonrpc


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

    def make_fun(name, value):
        @jsonrpc.listener(value, name)
        def fun(incoming: Optional[Incoming], outgoing: Optional[Outgoing]):
            if incoming:
                incoming.params.append('incoming-' + name)

            if outgoing:
                (outgoing.result if isinstance(outgoing, Response) else outgoing.params).append('outgoing-' + name)

    for event in Events:
        make_fun(event.name, event)
        make_fun(event.name + '-str', event.name)

    @jsonrpc
    def method(*params: str) -> List[str]:
        return [*params, 'method']

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'method', 'params': [], 'id': 1},
    {'jsonrpc': '2.0', 'result': [
        'incoming-all', 'incoming-all-str', 'incoming-incoming', 'incoming-incoming-str', 'incoming-post',
        'incoming-post-str', 'incoming-request', 'incoming-request-str', 'incoming-incoming_post',
        'incoming-incoming_post-str', 'incoming-incoming_request', 'incoming-incoming_request-str',
        'incoming-incoming_post_request', 'incoming-incoming_post_request-str', 'method', 'outgoing-all',
        'outgoing-all-str', 'outgoing-outgoing', 'outgoing-outgoing-str', 'outgoing-post', 'outgoing-post-str',
        'outgoing-response', 'outgoing-response-str', 'outgoing-outgoing_post', 'outgoing-outgoing_post-str',
        'outgoing-outgoing_response', 'outgoing-outgoing_response-str', 'outgoing-outgoing_post_response',
        'outgoing-outgoing_post_response-str'
    ], 'id': 1}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    data = await response.json()

    assert data == out


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'method', 'params': [], 'id': 1},
    {'jsonrpc': '2.0', 'result': [
        'incoming-all', 'incoming-all-str', 'incoming-incoming', 'incoming-incoming-str', 'incoming-ws',
        'incoming-ws-str', 'incoming-request', 'incoming-request-str', 'incoming-incoming_ws',
        'incoming-incoming_ws-str', 'incoming-incoming_request', 'incoming-incoming_request-str',
        'incoming-incoming_ws_request', 'incoming-incoming_ws_request-str', 'method', 'outgoing-all',
        'outgoing-all-str', 'outgoing-outgoing', 'outgoing-outgoing-str', 'outgoing-ws', 'outgoing-ws-str',
        'outgoing-response', 'outgoing-response-str', 'outgoing-outgoing_ws', 'outgoing-outgoing_ws-str',
        'outgoing-outgoing_response', 'outgoing-outgoing_response-str', 'outgoing-outgoing_ws_response',
        'outgoing-outgoing_ws_response-str'
    ], 'id': 1}
)])
async def test_ws(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    ws = await test_cli.ws_connect('/ws')
    await ws.send_json(in_)
    data = await ws.receive_json(timeout=0.01)
    await ws.close()
    await test_cli.close()

    assert data == out
