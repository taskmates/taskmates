from typing import List, Optional, Any

import pytest
import tiktoken

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

class Quote(GenericFakeChatModel):
    def __init__(self, **kwargs):
        super().__init__(messages=iter([]))

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ) -> ChatResult:
        last_message = messages[-1]
        content = getattr(last_message, "content", "")
        quoted_content = '\n'.join('> ' + line for line in content.split('\n'))
        quoted_content += "\n\n"
        message = AIMessage(content=quoted_content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ):
        last_message = messages[-1]
        content = getattr(last_message, "content", "")
        quoted_content = '\n'.join('> ' + line for line in content.split('\n'))
        quoted_content += "\n\n"
        enc = tiktoken.encoding_for_model("gpt-4")
        encoded = enc.encode(quoted_content)
        tokens = [enc.decode([token]) for token in encoded]
        yield ChatGenerationChunk(message=AIMessageChunk(role="assistant", content=""))
        for token in tokens:
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", response_metadata={"finish_reason": "stop"})
        )

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ):
        last_message = messages[-1]
        content = getattr(last_message, "content", "")
        quoted_content = '\n'.join('> ' + line for line in content.split('\n'))
        quoted_content += "\n\n"
        enc = tiktoken.encoding_for_model("gpt-4")
        encoded = enc.encode(quoted_content)
        tokens = [enc.decode([token]) for token in encoded]
        yield ChatGenerationChunk(message=AIMessageChunk(role="assistant", content=""))
        for token in tokens:
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", response_metadata={"finish_reason": "stop"})
        )

    @property
    def _llm_type(self) -> str:
        return "quote"

    @property
    def _identifying_params(self) -> dict:
        return {}

# TODO: fix it
# @pytest.mark.asyncio
# async def test_quote_stream_and_generate(tmp_path):
#     from langchain_core.messages import HumanMessage
#
#     quote = Quote()
#     messages = [HumanMessage(content="Short answer. 1 + 1=?\n\n")]
#
#     # Test generate (non-streaming)
#     result = quote._generate(messages)
#     assert result.generations[0].message.content == "> Short answer. 1 + 1=\n\n"
#
#     # Test streaming
#     chunks = list(quote._stream(messages))
#     assert chunks[0].message.role == "assistant"
#     tokens = [c.message.content for c in chunks if c.message.content not in (None, "")]
#     assert "".join(tokens) == "> Short answer. 1 + 1=?"
#     assert chunks[-1].message.finish_reason == "stop"
#
#     # Test async streaming
#     async_chunks = []
#     async for c in quote._astream(messages):
#         async_chunks.append(c)
#     assert async_chunks[0].message.role == "assistant"
#     tokens = [c.message.content for c in async_chunks if c.message.content not in (None, "")]
#     assert "".join(tokens) == "> Short answer. 1 + 1=?"
#     assert async_chunks[-1].message.finish_reason == "stop"
