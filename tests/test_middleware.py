from asyncio import TimeoutError, iscoroutine, wait_for
from functools import partial
from logging import DEBUG
from operator import contains
from typing import List, Optional

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from ujson import dumps, loads

from sanic_jsonrpc import Error, Notification, Notifier, Outgoing, Predicates, Request, Response, SanicJsonrpc

Sanic.test_mode = True


def lists_equal_unordered(self: list, other: list) -> bool:
    return all(map(partial(contains, other), self)) and all(map(partial(contains, self), other))


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')

    def make_middleware(name, value):
        @jsonrpc.middleware(value, name)
        def middleware(request: Optional[Request], response: Optional[Response], notification: Optional[Notification]):
            if request and request.method == 'all_predicates':
                request.params.append(name)

            if response and isinstance(response.result, list) and 'all_predicates' in response.result:
                response.result.append(name)

            if notification and notification.method == 'all_predicates_callback':
                notification.params.append(name)

    for predicate in Predicates:
        make_middleware(predicate.name, predicate)
        make_middleware(predicate.name, predicate.name)

    @jsonrpc
    def all_predicates(*params: str, notifier: Optional[Notifier]) -> List[str]:
        if notifier:
            notifier.send(Notification('all_predicates_callback', []))

        return [*params, 'all_predicates']

    @jsonrpc.middleware(Predicates.notification)
    def notification_middleware_exception_middleware(notification: Notification):
        if notification.method == 'notification_middleware_exception_callback':
            raise Exception('notification_middleware_exception_middleware')

    @jsonrpc.ws
    def notification_middleware_exception(notifier: Notifier):
        notifier.send(Notification('notification_middleware_exception_callback', None))

    @jsonrpc.middleware(Predicates.incoming)
    def incoming_middleware_error_middleware(request: Request):
        if request.method == 'incoming_middleware_error':
            raise Error(1234, 'incoming_middleware_error_middleware')

    @jsonrpc
    def incoming_middleware_error():
        pass

    @jsonrpc.middleware(Predicates.incoming)
    def incoming_middleware_exception_middleware(request: Request):
        if request.method == 'incoming_middleware_exception':
            raise Exception('incoming_middleware_exception_middleware')

    @jsonrpc
    def incoming_middleware_exception():
        pass

    @jsonrpc.middleware(Predicates.outgoing)
    def outgoing_middleware_error_middleware(request: Optional[Request]):
        if request and request.method == 'outgoing_middleware_error':
            raise Error(5678, 'outgoing_middleware_error_middleware')

    @jsonrpc
    def outgoing_middleware_error():
        pass

    @jsonrpc.middleware(Predicates.outgoing)
    def outgoing_middleware_exception_middleware(request: Optional[Request]):
        if request and request.method == 'outgoing_middleware_exception':
            raise Exception('outgoing_middleware_exception_middleware')

    @jsonrpc
    def outgoing_middleware_exception():
        pass

    @jsonrpc.middleware
    def no_predicate_middleware(
            request: Optional[Request],
            response: Optional[Response],
            notification: Optional[Notification],
    ):
        if request and request.method == 'no_predicate':
            request.params.append('no_predicate_middleware')

        if response and isinstance(response.result, list) and 'no_predicate' in response.result:
            response.result.append('no_predicate_middleware')

        if notification and notification.method == 'no_predicate_callback':
            notification.params.append('no_predicate_middleware')

    @jsonrpc
    def no_predicate(*params: str, notifier: Optional[Notifier]) -> List[str]:
        if notifier:
            notifier.send(Notification('no_predicate_callback', []))

        return [*params, 'no_predicate']

    @jsonrpc.middleware(Predicates.response)
    def response_middleware_middleware(request: Request, response: Response):
        if request.method == 'response_middleware':
            response.result = 'response_middleware_middleware'

    @jsonrpc
    def response_middleware():
        pass

    @jsonrpc.middleware(Predicates.outgoing)
    def response_middleware_middleware(request: Optional[Request], outgoing: Outgoing):
        if request:
            if request.method == 'outgoing_middleware':
                outgoing.result = 'outgoing_middleware_middleware'
        else:
            if outgoing.method == 'outgoing_middleware_callback':
                outgoing.params = 'outgoing_middleware_middleware'

    @jsonrpc
    def outgoing_middleware(notifier: Optional[Notifier]):
        if notifier:
            notifier.send(Notification('outgoing_middleware_callback'))

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app))


@fixture
def test_cli_ws(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, scheme='ws', protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'all_predicates', 'params': [], 'id': 1},
    {'jsonrpc': '2.0', 'result': [
        'any', 'any', 'incoming', 'incoming', 'post', 'post', 'request', 'request', 'incoming_post',
        'incoming_post', 'incoming_request', 'incoming_request', 'incoming_post_request', 'incoming_post_request',
        'all_predicates', 'any', 'any', 'outgoing', 'outgoing', 'post', 'post', 'response', 'response',
        'outgoing_post', 'outgoing_post', 'outgoing_response', 'outgoing_response', 'outgoing_post_response',
        'outgoing_post_response'
    ], 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_middleware_error', 'id': 2},
    {'jsonrpc': '2.0', 'error': {'code': 1234, 'message': 'incoming_middleware_error_middleware'}, 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'incoming_middleware_exception', 'id': 3},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 3}
), (
    {'jsonrpc': '2.0', 'method': 'outgoing_middleware_error', 'id': 4},
    {'jsonrpc': '2.0', 'error': {'code': 5678, 'message': 'outgoing_middleware_error_middleware'}, 'id': 4}
), (
    {'jsonrpc': '2.0', 'method': 'outgoing_middleware_exception', 'id': 5},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 5}
), (
    {'jsonrpc': '2.0', 'method': 'no_predicate', 'params': [], 'id': 6},
    {'jsonrpc': '2.0', 'result': ['no_predicate_middleware', 'no_predicate', 'no_predicate_middleware'], 'id': 6}
), (
    {'jsonrpc': '2.0', 'method': 'response_middleware', 'id': 7},
    {'jsonrpc': '2.0', 'result': 'response_middleware_middleware', 'id': 7}
), (
    {'jsonrpc': '2.0', 'method': 'outgoing_middleware', 'id': 8},
    {'jsonrpc': '2.0', 'result': 'outgoing_middleware_middleware', 'id': 8}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    data = response.json()
    data = (await data) if iscoroutine(data) else data

    assert data == out


@mark.parametrize('in_,out', [(
    [
        {'jsonrpc': '2.0', 'method': 'all_predicates', 'params': [], 'id': 1},
    ], [
        {'jsonrpc': '2.0', 'result': [
            'any', 'any', 'incoming', 'incoming', 'ws', 'ws', 'request', 'request', 'incoming_ws', 'incoming_ws',
            'incoming_request', 'incoming_request', 'incoming_ws_request', 'incoming_ws_request',
            'all_predicates', 'any', 'any', 'outgoing', 'outgoing', 'ws', 'ws', 'response', 'response',
            'outgoing_ws', 'outgoing_ws', 'outgoing_response', 'outgoing_response', 'outgoing_ws_response',
            'outgoing_ws_response'
        ], 'id': 1},
        {'jsonrpc': '2.0', 'method': 'all_predicates_callback', 'params': [
            'any', 'any', 'outgoing', 'outgoing', 'ws', 'ws', 'notification', 'notification', 'outgoing_ws',
            'outgoing_ws', 'outgoing_notification', 'outgoing_notification', 'outgoing_ws_notification',
            'outgoing_ws_notification'
        ]}

    ]
), (
    [{'jsonrpc': '2.0', 'method': 'notification_middleware_exception', 'id': 2}],
    [{'jsonrpc': '2.0', 'result': None, 'id': 2}]
), (
    [{'jsonrpc': '2.0', 'method': 'incoming_middleware_error', 'id': 3}],
    [{'jsonrpc': '2.0', 'error': {'code': 1234, 'message': 'incoming_middleware_error_middleware'}, 'id': 3}]
), (
    [{'jsonrpc': '2.0', 'method': 'incoming_middleware_exception', 'id': 4}],
    [{'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 4}]
), (
    [{'jsonrpc': '2.0', 'method': 'outgoing_middleware_error', 'id': 5}],
    [{'jsonrpc': '2.0', 'error': {'code': 5678, 'message': 'outgoing_middleware_error_middleware'}, 'id': 5}]
), (
    [{'jsonrpc': '2.0', 'method': 'outgoing_middleware_exception', 'id': 6}],
    [{'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 6}]
), (
    [
        {'jsonrpc': '2.0', 'method': 'no_predicate', 'params': [], 'id': 7}
    ],
    [
        {'jsonrpc': '2.0', 'result': ['no_predicate_middleware', 'no_predicate', 'no_predicate_middleware'], 'id': 7},
        {'jsonrpc': '2.0', 'method': 'no_predicate_callback', 'params': ['no_predicate_middleware']}
    ]
), (
    [{'jsonrpc': '2.0', 'method': 'response_middleware', 'id': 8}],
    [{'jsonrpc': '2.0', 'result': 'response_middleware_middleware', 'id': 8}]
), (
    [
        {'jsonrpc': '2.0', 'method': 'outgoing_middleware', 'params': [], 'id': 9}
    ],
    [
        {'jsonrpc': '2.0', 'result': 'outgoing_middleware_middleware', 'id': 9},
        {'jsonrpc': '2.0', 'method': 'outgoing_middleware_callback', 'params': 'outgoing_middleware_middleware'}
    ]
)])
async def test_ws(caplog, test_cli_ws, in_: List[dict], out: List[dict]):
    caplog.set_level(DEBUG)
    ws = await test_cli_ws.ws_connect('/ws')

    for data in in_:
        await ws.send(dumps(data))

    left = []

    while True:
        try:
            left.append(loads(await wait_for(ws.recv(), 0.05)))
        except TimeoutError:
            break

    await ws.close()
    await test_cli_ws.close()

    right = out

    assert lists_equal_unordered(left, right)
