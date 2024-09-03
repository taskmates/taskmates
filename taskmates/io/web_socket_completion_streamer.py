import json

from loguru import logger

from taskmates.core.signal_receiver import SignalReceiver
from taskmates.core.signals import Signals


class WebSocketCompletionStreamer(SignalReceiver):
    def __init__(self, websocket):
        self.websocket = websocket

    async def handle_completion(self, chunk):
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
        await self.websocket.send(dump)

    def connect(self, signals: Signals):
        signals.response.completion.connect(self.handle_completion, weak=False)

    def disconnect(self, signals: Signals):
        signals.response.completion.disconnect(self.handle_completion)
