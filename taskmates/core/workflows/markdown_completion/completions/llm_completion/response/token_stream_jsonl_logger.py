import json
import os
from typing import AsyncIterable

from langchain_core.messages import AIMessageChunk


class TokenStreamJsonlLogger:
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk], path: str):
        self.chat_completion = chat_completion
        self.path = path
        if os.path.exists(self.path):
            os.remove(self.path)

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            chunk_dict = chunk.model_dump()
            with open(self.path, "a") as f:
                f.write(json.dumps(chunk_dict, default=str) + "\n")
            yield chunk
