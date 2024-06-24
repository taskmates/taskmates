import re
from typing import AsyncIterable

from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel


class ChatCompletionPreProcessor:
    def __init__(self, chat_completion: AsyncIterable[ChatCompletionChunkModel]):
        self.chat_completion = chat_completion
        self.name = None

    async def __aiter__(self):
        index = -1
        async for chunk in self.chat_completion:
            index += 1
            if chunk.choices[0].delta.content is None:
                yield chunk
                continue

            content = chunk.choices[0].delta.content

            if index == 1:
                content = content.lstrip(" ")
                if content and not re.match(r'^[a-zA-Z0-9\n]', content):
                    content = "\n" + content
                chunk.choices[0].delta.content = content

            yield chunk
