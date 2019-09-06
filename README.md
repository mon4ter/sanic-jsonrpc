# sanic-jsonrpc
[![PyPI version](https://img.shields.io/pypi/v/sanic-jsonrpc.svg)](https://pypi.org/project/sanic-jsonrpc)
[![Python version](https://img.shields.io/pypi/pyversions/sanic-jsonrpc.svg)](https://pypi.org/project/sanic-jsonrpc)

JSON-RPC 2.0 support for Sanic over HTTP and WebSocket

## Example

### server.py
```python
from sanic import Sanic
from sanic_jsonrpc import Jsonrpc

app = Sanic()
jsonrpc = Jsonrpc(app, post_route='/api/rpc/post', ws_route='/api/rpc/ws')

@jsonrpc
def sub(a: int, b: int) -> int:
    return a - b

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)
```

### client.py
```python
from asyncio import get_event_loop

from aiohttp import ClientSession

async def main():
    url = 'http://127.0.0.1:8000/api/rpc'
    request = {'jsonrpc': '2.0', 'method': 'sub', 'params': [42, 23], 'id': 1}

    async with ClientSession() as session:
        async with session.post(url + '/post', json=request) as resp:
            response = await resp.json()
            print(response['result'])  # 19

        async with session.ws_connect(url + '/ws') as ws:
            await ws.send_json(request)
            response = await ws.receive_json()
            print(response['result'])  # 19
            
if __name__ == '__main__':
    get_event_loop().run_until_complete(main())
```