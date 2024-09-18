import asyncio
import json
import signal

import websockets
from websockets.exceptions import ConnectionClosed

from taskmates.types import ClientConfig
from taskmates.core.execution_context import EXECUTION_CONTEXT


async def on_message(message):
    payload = json.loads(message)

    if payload["type"] == "markdown_chunk":
        print(payload["payload"]["markdown_chunk"], end="")


async def send_signal(ws, signal_type, request_id):
    await ws.send(json.dumps({
        "type": signal_type,
        "context": {
            "request_id": request_id
        },
    }))


# noinspection PyUnusedLocal
def signal_handler(sig, frame):
    # noinspection PyGlobalUndefined
    global received_signal
    received_signal = sig


async def receive_messages(websocket):
    while True:
        try:
            message = await websocket.recv()
            await on_message(message)
        except ConnectionClosed:
            break


# noinspection PyShadowingNames
async def handle_signals(websocket, request_id, received_signal):
    while True:
        if received_signal == signal.SIGINT:
            print("Interrupting...")
            print("Press Ctrl+C again to kill")
            await send_signal(websocket, "interrupt", request_id)
            await asyncio.sleep(5)
            received_signal = None
        elif received_signal == signal.SIGTERM:
            await send_signal(websocket, "kill", request_id)
            await asyncio.sleep(5)
            break
        await asyncio.sleep(0.1)


async def perform_websocket_completion(markdown, client_config: ClientConfig):
    # TODO handle `full` arg

    async with websockets.connect(client_config['endpoint']) as websocket:
        try:
            context = EXECUTION_CONTEXT.get().contexts["completion_context"]

            await websocket.send(json.dumps({
                "type": "completions_request",
                "markdown_chat": markdown,
                "context": context
            }))

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            receive_task = asyncio.create_task(receive_messages(websocket))
            signal_task = asyncio.create_task(handle_signals(websocket, context['request_id'], received_signal))

            done, pending = await asyncio.wait(
                [receive_task, signal_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

        except ConnectionClosed:
            pass
        except Exception as e:
            print(e)
