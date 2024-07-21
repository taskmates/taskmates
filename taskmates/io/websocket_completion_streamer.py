import json

from loguru import logger
from quart import websocket

from taskmates.signals.signals import Signals


class WebsocketCompletionStreamer:
    def connect(self, signals: Signals):
        signals.response.completion.connect(self.handle_complete, weak=False)

    def disconnect(self, signals: Signals):
        signals.response.completion.disconnect(self.handle_complete)

    @staticmethod
    async def handle_complete(chunk):
        if chunk is None:
            return
        logger.debug(f"response {chunk!r}")
        dump = json.dumps({
            "type": "completion",
            "payload": {
                "markdown_chunk": chunk
            }
        }, ensure_ascii=False)
        dump = dump.replace("\r", "")
        await websocket.send(dump)
