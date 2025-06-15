import json
from typing import List, Optional, Any, Iterator, AsyncIterator

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk

from taskmates.lib.root_path.root_path import root_path


class FixtureChatModel(BaseChatModel):
    """A fake chat model that loads responses from fixture files."""

    fixture_path: str
    """Path to the fixture file relative to the project root."""

    class Config:
        """Configuration for this pydantic object."""
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "fixture"

    def bind_tools(self, tools, **kwargs):
        """Return self as bind_tools is a no-op for fixtures."""
        return self

    def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat response synchronously."""
        # Load non-streaming response
        resolved_path = root_path() / self.fixture_path

        if resolved_path.suffix == '.json':
            # Non-streaming response
            with open(resolved_path, "r") as f:
                data = json.load(f)

            # Create AIMessage from the data
            message = AIMessage(
                content=data.get("content", ""),
                additional_kwargs=data.get("additional_kwargs", {}),
                response_metadata=data.get("response_metadata", {}),
                name=data.get("name"),
                id=data.get("id")
            )

            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
        else:
            # For streaming fixtures in sync mode, concatenate all chunks
            chunks = []
            with open(resolved_path, "r") as f:
                for line in f:
                    if line.strip():
                        chunks.append(json.loads(line))

            # Combine chunks into a single message
            combined_content = "".join(chunk.get("content", "") for chunk in chunks)
            # Take metadata from the last chunk with finish_reason
            last_chunk = chunks[-1] if chunks else {}

            message = AIMessage(
                content=combined_content,
                additional_kwargs=last_chunk.get("additional_kwargs", {}),
                response_metadata=last_chunk.get("response_metadata", {}),
                name=last_chunk.get("name"),
                id=last_chunk.get("id")
            )

            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])

    async def _agenerate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat response asynchronously."""
        # For non-streaming, just call sync version
        return self._generate(messages, stop, run_manager, **kwargs)

    def _stream(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream chat response chunks synchronously."""
        resolved_path = root_path() / self.fixture_path

        if resolved_path.suffix == '.jsonl':
            # Streaming response
            with open(resolved_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        chunk = AIMessageChunk(
                            content=data.get("content", ""),
                            additional_kwargs=data.get("additional_kwargs", {}),
                            response_metadata=data.get("response_metadata", {}),
                            name=data.get("name"),
                            id=data.get("id")
                        )
                        yield ChatGenerationChunk(message=chunk)
        else:
            # Non-streaming file, yield as single chunk
            with open(resolved_path, "r") as f:
                data = json.load(f)

            chunk = AIMessageChunk(
                content=data.get("content", ""),
                additional_kwargs=data.get("additional_kwargs", {}),
                response_metadata=data.get("response_metadata", {}),
                name=data.get("name"),
                id=data.get("id")
            )
            yield ChatGenerationChunk(message=chunk)

    async def _astream(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Stream chat response chunks asynchronously."""
        resolved_path = root_path() / self.fixture_path

        if resolved_path.suffix == '.jsonl':
            # Streaming response
            with open(resolved_path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        chunk = AIMessageChunk(
                            content=data.get("content", ""),
                            additional_kwargs=data.get("additional_kwargs", {}),
                            response_metadata=data.get("response_metadata", {}),
                            name=data.get("name"),
                            id=data.get("id"),
                            tool_calls=data.get("tool_calls", []),
                            tool_call_chunks=data.get("tool_call_chunks", [])
                        )
                        yield ChatGenerationChunk(message=chunk)
        else:
            # Non-streaming file, yield as single chunk
            with open(resolved_path, "r") as f:
                data = json.load(f)

            chunk = AIMessageChunk(
                content=data.get("content", ""),
                additional_kwargs=data.get("additional_kwargs", {}),
                response_metadata=data.get("response_metadata", {}),
                name=data.get("name"),
                id=data.get("id")
            )
            yield ChatGenerationChunk(message=chunk)


@pytest.mark.asyncio
async def test_fixture_chat_model_streaming():
    """Test that FixtureChatModel properly streams chunks."""
    model = FixtureChatModel(fixture_path="tests/fixtures/api-responses/streaming_response.jsonl")

    chunks = []
    async for chunk in model._astream([]):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert all(isinstance(chunk, ChatGenerationChunk) for chunk in chunks)
    # Verify we get the expected content
    full_content = "".join(chunk.message.content for chunk in chunks)
    assert "1, 2, 3, 4, 5" in full_content


@pytest.mark.asyncio
async def test_fixture_chat_model_non_streaming():
    """Test that FixtureChatModel handles non-streaming responses."""
    model = FixtureChatModel(fixture_path="tests/fixtures/api-responses/non_streaming_response.json")

    result = await model._agenerate([])

    assert len(result.generations) == 1
    message = result.generations[0].message
    assert isinstance(message, AIMessage)
    assert message.content == "1, 2, 3, 4, 5"
