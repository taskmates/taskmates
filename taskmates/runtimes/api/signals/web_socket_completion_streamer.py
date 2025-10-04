import json

from loguru import logger
from quart import Websocket


class WebSocketCompletionStreamer:
    def __init__(self, websocket: Websocket):
        super().__init__()
        self.websocket = websocket

    async def handle_completion(self, sender, value):
        chunk = value
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
