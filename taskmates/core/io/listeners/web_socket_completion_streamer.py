import json

from loguru import logger

from taskmates.core.processor import Processor
from taskmates.core.execution_context import EXECUTION_CONTEXT


class WebSocketCompletionStreamer(Processor):
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

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.response.stdout.connect(self.handle_completion, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.response.stdout.disconnect(self.handle_completion)
