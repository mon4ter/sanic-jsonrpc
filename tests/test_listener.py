from asyncio import TimeoutError
from functools import partial
from logging import DEBUG
from operator import contains
from typing import List, Optional

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol

from sanic_jsonrpc import Error, Events, Incoming, Notification, Notifier, Outgoing, Request, Response, SanicJsonrpc


def lists_equal_unordered(self: list, other: list) -> bool:
    return all(map(partial(contains, other), self)) and all(map(partial(contains, self), other))


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

    def make_fun(name, value):
        @jsonrpc.listener(value, name)
        def fun(incoming: Optional[Incoming], outgoing: Optional[Outgoing]):
            if incoming and incoming.method == 'all_listeners':
                incoming.params.append('incoming-' + name)

            if isinstance(outgoing, Response) and isinstance(outgoing.result, list) and 'all_listeners' in outgoing.result:
                outgoing.result.append('outgoing-' + name)
            elif isinstance(outgoing, Notification) and outgoing.method == 'all_listeners_callback':
                outgoing.params.append('outgoing-' + name)

    for event in Events:
        make_fun(event.name, event)
        make_fun(event.name + '-str', event.name)

    @jsonrpc
    def all_listeners(*params: str, notifier: Optional[Notifier]) -> List[str]:
        if notifier:
            notifier.send(Notification('all_listeners_callback', []))

        return [*params, 'all_listeners']

    @jsonrpc.listener(Events.notification)
    async def notification_listener_exception_listener(notification: Notification):
        if notification.method == 'notification_listener_exception_callback':
            raise Exception('notification_listener_exception_listener')

    @jsonrpc.ws
    def notification_listener_exception(notifier: Notifier):
        notifier.send(Notification('notification_listener_exception_callback', None))

    @jsonrpc.listener(Events.incoming)
    async def incoming_listener_error_listener(request: Request):
        if request.method == 'incoming_listener_error':
            raise Error(1234, 'incoming_listener_error_listener')

    @jsonrpc
    def incoming_listener_error():
        pass

    @jsonrpc.listener(Events.incoming)
    async def incoming_listener_exception_listener(request: Request):
        if request.method == 'incoming_listener_exception':
            raise Exception('incoming_listener_exception_listener')

    @jsonrpc
    def incoming_listener_exception():
        pass

    @jsonrpc.listener(Events.outgoing)
    async def outgoing_listener_error_listener(request: Optional[Request]):
        if request and request.method == 'outgoing_listener_error':
            raise Error(5678, 'outgoing_listener_error_listener')

    @jsonrpc
    def outgoing_listener_error():
        pass

    @jsonrpc.listener(Events.outgoing)
    async def outgoing_listener_exception_listener(request: Optional[Request]):
        if request and request.method == 'outgoing_listener_exception':
            raise Exception('outgoing_listener_exception_listener')

    @jsonrpc
    def outgoing_listener_exception():
        pass

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'all_listeners', 'params': [], 'id': 1},
    {'jsonrpc': '2.0', 'result': [
        'incoming-all', 'incoming-all-str', 'incoming-incoming', 'incoming-incoming-str', 'incoming-post',
        'incoming-post-str', 'incoming-request', 'incoming-request-str', 'incoming-incoming_post',
        'incoming-incoming_post-str', 'incoming-incoming_request', 'incoming-incoming_request-str',
        'incoming-incoming_post_request', 'incoming-incoming_post_request-str', 'all_listeners', 'outgoing-all',
        'outgoing-all-str', 'outgoing-outgoing', 'outgoing-outgoing-str', 'outgoing-post', 'outgoing-post-str',
        'outgoing-response', 'outgoing-response-str', 'outgoing-outgoing_post', 'outgoing-outgoing_post-str',
        'outgoing-outgoing_response', 'outgoing-outgoing_response-str', 'outgoing-outgoing_post_response',
        'outgoing-outgoing_post_response-str'
    ], 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_listener_error', 'id': 2},
    {'jsonrpc': '2.0', 'error': {'code': 1234, 'message': 'incoming_listener_error_listener'}, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_listener_exception', 'id': 3},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'outgoing_listener_error', 'id': 4},
    {'jsonrpc': '2.0', 'error': {'code': 5678, 'message': 'outgoing_listener_error_listener'}, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'outgoing_listener_exception', 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 5}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    data = await response.json()

    assert data == out


@mark.parametrize('in_,out', [(
    [
        {'jsonrpc': '2.0', 'method': 'all_listeners', 'params': [], 'id': 1},
    ], [
        {'jsonrpc': '2.0', 'result': [
            'incoming-all', 'incoming-all-str', 'incoming-incoming', 'incoming-incoming-str', 'incoming-ws',
            'incoming-ws-str', 'incoming-request', 'incoming-request-str', 'incoming-incoming_ws',
            'incoming-incoming_ws-str', 'incoming-incoming_request', 'incoming-incoming_request-str',
            'incoming-incoming_ws_request', 'incoming-incoming_ws_request-str', 'all_listeners', 'outgoing-all',
            'outgoing-all-str', 'outgoing-outgoing', 'outgoing-outgoing-str', 'outgoing-ws', 'outgoing-ws-str',
            'outgoing-response', 'outgoing-response-str', 'outgoing-outgoing_ws', 'outgoing-outgoing_ws-str',
            'outgoing-outgoing_response', 'outgoing-outgoing_response-str', 'outgoing-outgoing_ws_response',
            'outgoing-outgoing_ws_response-str'
        ], 'id': 1},
        {'jsonrpc': '2.0', 'method': 'all_listeners_callback', 'params': [
            'outgoing-all', 'outgoing-all-str', 'outgoing-outgoing', 'outgoing-outgoing-str', 'outgoing-ws',
            'outgoing-ws-str', 'outgoing-notification', 'outgoing-notification-str', 'outgoing-outgoing_ws',
            'outgoing-outgoing_ws-str', 'outgoing-outgoing_notification', 'outgoing-outgoing_notification-str',
            'outgoing-outgoing_ws_notification', 'outgoing-outgoing_ws_notification-str'
        ]}

    ]
), (
    [{'jsonrpc': '2.0', 'method': 'notification_listener_exception', 'id': 2}],
    [{'jsonrpc': '2.0', 'result': None, 'id': 2}]
), (
    [{'jsonrpc': '2.0', 'method': 'incoming_listener_error', 'id': 3}],
    [{'jsonrpc': '2.0', 'error': {'code': 1234, 'message': 'incoming_listener_error_listener'}, 'id': 3}]
), (
    [{'jsonrpc': '2.0', 'method': 'incoming_listener_exception', 'id': 4}],
    [{'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 4}]
), (
    [{'jsonrpc': '2.0', 'method': 'outgoing_listener_error', 'id': 5}],
    [{'jsonrpc': '2.0', 'error': {'code': 5678, 'message': 'outgoing_listener_error_listener'}, 'id': 5}]
), (
    [{'jsonrpc': '2.0', 'method': 'outgoing_listener_exception', 'id': 6}],
    [{'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 6}]
)])
async def test_ws(caplog, test_cli, in_: List[dict], out: List[dict]):
    caplog.set_level(DEBUG)
    ws = await test_cli.ws_connect('/ws')

    for data in in_:
        await ws.send_json(data)

    left = []

    while True:
        try:
            left.append(await ws.receive_json(timeout=0.05))
        except TimeoutError:
            break

    await ws.close()
    await test_cli.close()

    right = out

    assert lists_equal_unordered(left, right)
