import json
from abc import ABC

from pydantic import BaseModel
from quart import websocket


class StreamingSink(ABC):
    async def process(self, token):
        raise NotImplementedError


class WebsocketStreamingSink(BaseModel, StreamingSink):
    class Config:
        arbitrary_types_allowed = True

    def connect(self, signals):
        signals.completion.connect(self.send_completion, weak=False)
        return self

    @staticmethod
    async def send_completion(chunk):
        if chunk is None:
            return
        # print(f"response {chunk!r}")
        dump = json.dumps({
            "type": "completion",
            "payload": {
                "markdown_chunk": chunk
            }
        }, ensure_ascii=False)
        dump = dump.replace("\r", "")
        await websocket.send(dump)


class StdoutStreamingSink(StreamingSink):
    def __init__(self):
        super().__init__()
        self.current_key = None

    async def process(self, token):
        if token is not None:
            print(token, end="", flush=True)
        else:
            print("")
