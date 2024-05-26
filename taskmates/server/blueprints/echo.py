import tiktoken
from quart import Blueprint, websocket

echo_pb = Blueprint("echo", __name__)


@echo_pb.websocket('/echo')
async def echo():
    while True:
        message = await websocket.receive()
        print(f'Received message: {message}')

        enc = tiktoken.get_encoding("o200k_base")
        encoded = enc.encode(message)
        for token in encoded:
            await websocket.send(enc.decode([token]))


@echo_pb.websocket('/echo/error')
async def echo_error():
    while True:
        message = await websocket.receive()
        print(f'Received message: {message}')
        raise Exception("An Error")


@echo_pb.websocket('/echo/close')
async def echo_close():
    while True:
        message = await websocket.receive()
        print(f'Received message: {message}')
        await websocket.close(1000, "OK")
