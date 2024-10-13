import json

from loguru import logger

from taskmates.core.daemon import Daemon
from taskmates.core.run import RUN


class WebSocketCompletionStreamer(Daemon):
    def __init__(self, websocket):
        super().__init__()
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
        stdout = RUN.get().output_streams.stdout
        self.exit_stack.enter_context(stdout.connected_to(self.handle_completion))
