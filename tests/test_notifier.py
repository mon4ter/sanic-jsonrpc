from asyncio import TimeoutError, sleep, ensure_future
from functools import partial
from logging import DEBUG
from operator import contains
from typing import List

from pytest import fixture, mark
from sanic import Sanic
from sanic.websocket import WebSocketProtocol
from websockets import ConnectionClosed

from sanic_jsonrpc import SanicJsonrpc, Notifier, Notification

Sanic.test_mode = True


def lists_equal_unordered(self: list, other: list) -> bool:
    return all(map(partial(contains, other), self)) and all(map(partial(contains, self), other))


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post', '/ws')
    tasks = set()

    @app_.listener('before_server_stop')
    async def end_tasks(_app, _loop):
        for task in tasks:
            try:
                await task
            except ConnectionClosed:
                pass

    @jsonrpc
    def send_nowait(notifier: Notifier):
        notifier.send(Notification('send_nowait', None))

    @jsonrpc
    async def send_wait(notifier: Notifier):
        await notifier.send(Notification('send_wait', None))

    @jsonrpc
    def cancel(notifier: Notifier):
        notifier.send(Notification('cancel', None))
        notifier.cancel()

    async def subscription(notifier: Notifier):
        while not notifier.closed:
            await notifier.send(Notification('subscription', None))
            await sleep(0.1)

    @jsonrpc
    def subscribe(notifier: Notifier):
        tasks.add(ensure_future(subscription(notifier)))

    async def send(notifier: Notifier):
        await sleep(0.1)
        await notifier.send(Notification('send', None))

    @jsonrpc
    def send_closed(notifier: Notifier):
        tasks.add(ensure_future(send(notifier)))

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


@mark.parametrize('in_,out', [(
    [
        {'jsonrpc': '2.0', 'method': 'send_nowait', 'id': 1},
    ], [
        {'jsonrpc': '2.0', 'result': None, 'id': 1},
        {'jsonrpc': '2.0', 'method': 'send_nowait', 'params': None},
    ]
), (
    [
        {'jsonrpc': '2.0', 'method': 'send_wait', 'id': 2},
    ], [
        {'jsonrpc': '2.0', 'result': None, 'id': 2},
        {'jsonrpc': '2.0', 'method': 'send_wait', 'params': None},
    ]
), (
    [
        {'jsonrpc': '2.0', 'method': 'cancel', 'id': 3},
    ], [
        {'jsonrpc': '2.0', 'result': None, 'id': 3},
    ]
), (
    [
        {'jsonrpc': '2.0', 'method': 'subscribe', 'id': 4},
    ], [
        {'jsonrpc': '2.0', 'result': None, 'id': 4},
        {'jsonrpc': '2.0', 'method': 'subscription', 'params': None},
    ]
), (
    [
        {'jsonrpc': '2.0', 'method': 'send_closed', 'id': 5},
    ], [
        {'jsonrpc': '2.0', 'result': None, 'id': 5},
    ]
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
