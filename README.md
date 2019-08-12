# sanic-jsonrpc
JSON-RPC 2.0 support for Sanic over HTTP and WebSocket

## Example

### server.py
```python
from sanic import Sanic
from sanic_jsonrpc import Jsonrpc

app = Sanic()
jsonrpc = Jsonrpc(app, '/api/rpc/post', '/api/rpc/ws')

@jsonrpc
def add(a: int, b: int) -> int:
    return a + b
    
@jsonrpc.method
def sub(a: int, b: int) -> int:
    return a - b

@jsonrpc.method('Mul')
def mul(a: int, b: int) -> int:
    return a * b
    
@jsonrpc.post
def div(a: int, b: int) -> int:
    return a // b
    
@jsonrpc.ws
def echo(msg: str) -> str:
    return msg * 2

class Pair:
    def __init__(self, first: int, second: int):
        self.first = int(first)
        self.second = int(second)

@jsonrpc
async def concat(pair: Pair) -> str:
    return '{}.{}'.format(pair.first, pair.second)
    
@jsonrpc('Concat', p=Pair, result=str)
async def con(p):
    return '{}.{}'.format(p.first, p.second)

app.run(host='0.0.0.0', port=8000, debug=True)
```
