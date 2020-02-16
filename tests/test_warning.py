from pytest import deprecated_call
from sanic import Sanic

from sanic_jsonrpc import Jsonrpc


def test_jsonrpc_deprecation_warning():
    with deprecated_call():
        app = Sanic('sanic-jsonrpc')
        Jsonrpc(app, '/post', '/ws')
