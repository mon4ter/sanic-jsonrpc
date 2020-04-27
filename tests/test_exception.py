from logging import DEBUG

from pytest import fixture, mark
from sanic import Sanic

from sanic_jsonrpc import Error, SanicJsonrpc


class TestExceptionError(Exception):
    pass


class TestExceptionResult(Exception):
    pass


class TestExceptionException(Exception):
    pass


@fixture
def app():
    app_ = Sanic('sanic-jsonrpc')
    jsonrpc = SanicJsonrpc(app_, '/post')

    @jsonrpc.exception(TestExceptionError)
    def test_exception_error_exception(exc: TestExceptionError):
        return Error(exc.args[0], 'test_exception_error_exception')

    @jsonrpc
    def test_exception_error():
        raise TestExceptionError(4455)

    @jsonrpc.exception(TestExceptionResult)
    def test_exception_result_exception(exc: TestExceptionResult):
        return exc.args[0], 'test_exception_result_exception'

    @jsonrpc
    def test_exception_result():
        raise TestExceptionResult(8899)

    @jsonrpc.exception(TestExceptionException)
    def test_exception_exception_exception(exc: TestExceptionException):
        raise exc

    @jsonrpc
    def test_exception_exception():
        raise TestExceptionException

    return app_


@fixture
def test_cli(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app))


@mark.parametrize('in_,out', [(
    {'jsonrpc': '2.0', 'method': 'test_exception_error', 'id': 1},
    {'jsonrpc': '2.0', 'error': {'code': 4455, 'message': 'test_exception_error_exception'}, 'id': 1}
), (
    {'jsonrpc': '2.0', 'method': 'test_exception_result', 'id': 2},
    {'jsonrpc': '2.0', 'result': [8899, 'test_exception_result_exception'], 'id': 2}
), (
    {'jsonrpc': '2.0', 'method': 'test_exception_exception', 'id': 3},
    {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': 3}
)])
async def test_post(caplog, test_cli, in_: dict, out: dict):
    caplog.set_level(DEBUG)
    response = await test_cli.post('/post', json=in_)
    data = await response.json()

    assert data == out
