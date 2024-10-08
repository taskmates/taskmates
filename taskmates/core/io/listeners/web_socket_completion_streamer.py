import json

from loguru import logger

from taskmates.core.daemon import Daemon
from taskmates.core.run import RUN
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


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
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.output_streams.stdout.connected_to(self.handle_completion)
        ]))
