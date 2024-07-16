import json

from loguru import logger
from pydantic import BaseModel
from quart import websocket

from taskmates.signals import Signals
from taskmates.sinks.streaming_sink import StreamingSink


class WebsocketSignalBridge(BaseModel, StreamingSink):
    class Config:
        arbitrary_types_allowed = True

    def connect(self, signals: Signals):
        signals.completion.connect(self.send_completion, weak=False)
        return self

    @staticmethod
    async def send_completion(chunk):
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
        try:
            await websocket.send(dump)
        except Exception as e:
            logger.error(f"Failed to send completion: {str(e)}")
