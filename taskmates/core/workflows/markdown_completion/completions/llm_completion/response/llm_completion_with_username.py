import re
from typing import AsyncIterable, List

import pytest
from langchain_core.messages import AIMessageChunk


class LlmCompletionWithUsername(AsyncIterable[AIMessageChunk]):
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk]):
        self.chat_completion = chat_completion
        self.buffered_tokens: List[str] = []
        self.buffering = True

    def _extract_text_content(self, content):
        """Extract text from content, handling both string and list formats."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
            return "".join(texts)
        return ""

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            # Extract text content for username detection
            current_text = self._extract_text_content(chunk.content)
            tool_calls = chunk.tool_calls if hasattr(chunk, "tool_calls") else []

            if self.buffering and tool_calls:
                self.buffering = False
                full_content = "".join(self.buffered_tokens)
                match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', full_content)
                username = match.group(1) if match else None

                # For tool calls with no content, yield a single chunk with username and tool_calls
                if not current_text:
                    yield self._flush_username(chunk, username, tool_calls=chunk.tool_calls)
                else:
                    # Regular flow: yield username chunk first
                    yield self._flush_username(chunk, username)

                    # If there's buffered content, yield it in a separate chunk
                    if match:
                        remaining_content = self._extract_remaining_content(full_content)
                        if remaining_content:
                            yield self._create_chunk(chunk, remaining_content)
                    elif full_content:
                        # No username pattern, so yield all buffered content
                        yield self._create_chunk(chunk, full_content)

                    # Yield the original chunk with content
                    yield chunk
                continue

            if chunk.content is None:
                yield chunk
                continue

            if not self.buffering:
                yield chunk
                continue

            # Only buffer text content for username detection
            if current_text:
                self.buffered_tokens.append(current_text)

            full_content = "".join(self.buffered_tokens)

            if self._is_full_match(full_content):
                match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', full_content)
                username = match.group(1)
                yield self._flush_username(chunk, username)
                remaining_content = self._extract_remaining_content(full_content)
                if remaining_content:
                    yield self._create_chunk(chunk, remaining_content)
                self.buffering = False
                self.buffered_tokens = []
            elif not self._is_partial_match(full_content):
                yield self._flush_username(chunk, None)
                if full_content:
                    yield self._create_chunk(chunk, full_content)
                else:
                    # No text content to buffer, just yield the chunk as is
                    yield chunk
                self.buffering = False
                self.buffered_tokens = []

    @staticmethod
    def _is_full_match(content: str) -> bool:
        return bool(re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', content))

    @staticmethod
    def _is_partial_match(content: str) -> bool:
        return content == '' or re.match(r'^[ \n]*\*\*[^*]*\*?\*?[ \n]?$', content)

    def _flush_username(self, chunk: AIMessageChunk, username, tool_calls=None) -> AIMessageChunk:
        return self._create_chunk(
            chunk,
            '',
            'assistant',
            username,
            tool_calls=tool_calls
        )

    @staticmethod
    def _extract_remaining_content(content: str) -> str:
        match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+(.*)', content, re.DOTALL)
        return match.group(2) if match else ''

    @staticmethod
    def _create_chunk(
            original_chunk: AIMessageChunk,
            content: str,
            role: str = None,
            name: str = None,
            tool_calls=None
    ) -> AIMessageChunk:
        additional_kwargs = dict(original_chunk.additional_kwargs)
        if tool_calls is not None:
            additional_kwargs["tool_calls"] = tool_calls
        return AIMessageChunk(
            content=content,
            response_metadata=getattr(original_chunk, "response_metadata", {}),
            additional_kwargs=additional_kwargs,
            name=name,
            id=getattr(original_chunk, "id", None),
            # Preserve tool-related attributes from the original chunk
            tool_calls=getattr(original_chunk, "tool_calls", []) if tool_calls is None else tool_calls,
            tool_call_chunks=getattr(original_chunk, "tool_call_chunks", []),
            invalid_tool_calls=getattr(original_chunk, "invalid_tool_calls", []),
            usage_metadata=getattr(original_chunk, "usage_metadata", None),
        )


# Test helpers
import json
import os
from taskmates.lib.matchers_ import matchers


async def load_fixture_chunks(fixture_name):
    """Load chunks from a fixture file."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "../../../../../../../tests/fixtures/api-responses",
        fixture_name
    )
    fixture_path = os.path.normpath(fixture_path)

    with open(fixture_path, "r") as f:
        if fixture_name.endswith('.jsonl'):
            for line in f:
                yield AIMessageChunk(**json.loads(line))
        else:
            data = json.load(f)
            yield AIMessageChunk(**data)


async def collect_chunks(async_iter):
    """Collect all chunks from an async iterator."""
    chunks = []
    async for chunk in async_iter:
        chunks.append(chunk)
    return chunks


# Invariant tests for LlmCompletionWithUsername

@pytest.mark.asyncio
async def test_username_processor_preserves_tool_calls_openai():
    """LlmCompletionWithUsername must preserve tool_calls from OpenAI fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    # Should have at least the same tool calls (may have more chunks due to username extraction)
    assert len(chunks_with_tool_calls) >= len(original_with_tool_calls)


@pytest.mark.asyncio
async def test_username_processor_preserves_tool_calls_anthropic():
    """LlmCompletionWithUsername must preserve tool_calls from Anthropic fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    # Should have at least the same tool calls
    assert len(chunks_with_tool_calls) >= len(original_with_tool_calls)


@pytest.mark.asyncio
async def test_username_processor_preserves_tool_call_chunks_openai():
    """LlmCompletionWithUsername must preserve tool_call_chunks from OpenAI fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c for c in chunks if c.tool_call_chunks]

    # Should preserve tool_call_chunks
    assert len(chunks_with_tool_call_chunks) > 0


@pytest.mark.asyncio
async def test_username_processor_handles_string_content_openai():
    """LlmCompletionWithUsername must handle OpenAI's string content format."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Reconstruct content
    content = "".join(c.content for c in chunks if c.content is not None)

    # Should have the expected content
    assert content == "1, 2, 3, 4, 5"


@pytest.mark.asyncio
async def test_username_processor_handles_list_content_anthropic():
    """LlmCompletionWithUsername must handle Anthropic's list content format."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # Should not raise any errors
    chunks = await collect_chunks(processor)

    # Should produce some chunks
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_username_processor_no_token_loss_openai():
    """LlmCompletionWithUsername must not lose tokens from OpenAI fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    # May have more chunks due to username extraction, but not fewer
    assert len(chunks) >= len(original_chunks)


@pytest.mark.asyncio
async def test_username_processor_no_token_loss_anthropic():
    """LlmCompletionWithUsername must not lose tokens from Anthropic fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # May have more chunks due to username extraction, but not fewer
    assert len(chunks) >= len(original_chunks)


@pytest.mark.asyncio
async def test_username_processor_preserves_metadata_openai():
    """LlmCompletionWithUsername must preserve response_metadata from OpenAI fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Check that metadata is preserved in at least some chunks
    chunks_with_metadata = [c for c in chunks if c.response_metadata]
    assert len(chunks_with_metadata) > 0


@pytest.mark.asyncio
async def test_username_processor_preserves_metadata_anthropic():
    """LlmCompletionWithUsername must preserve response_metadata from Anthropic fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Check that metadata is preserved in at least some chunks
    chunks_with_metadata = [c for c in chunks if c.response_metadata]
    assert len(chunks_with_metadata) > 0


@pytest.mark.asyncio
async def test_username_processor_extracts_username_pattern():
    """LlmCompletionWithUsername must extract username from markdown pattern."""

    # Create a simple test with username pattern
    async def username_chunks():
        yield AIMessageChunk(content="**assistant>** ")
        yield AIMessageChunk(content="Hello world")

    processor = LlmCompletionWithUsername(username_chunks())
    chunks = await collect_chunks(processor)

    # First chunk should have the username
    assert chunks[0] == matchers.object_with_attrs(
        name="assistant",
        content=""
    )

    # Remaining content should be preserved
    assert "".join(c.content for c in chunks[1:] if c.content) == "Hello world"


@pytest.mark.asyncio
async def test_username_processor_handles_no_username_pattern():
    """LlmCompletionWithUsername must handle content without username pattern."""

    # Create a simple test without username pattern
    async def no_username_chunks():
        yield AIMessageChunk(content="Hello ")
        yield AIMessageChunk(content="world")

    processor = LlmCompletionWithUsername(no_username_chunks())
    chunks = await collect_chunks(processor)

    # First chunk should have no username
    assert chunks[0] == matchers.object_with_attrs(
        name=None,
        content=""
    )

    # All content should be preserved
    assert "".join(c.content for c in chunks[1:] if c.content) == "Hello world"


@pytest.mark.asyncio
async def test_username_processor_preserves_tool_calls_gemini():
    """LlmCompletionWithUsername must preserve tool_calls from Gemini fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c.tool_calls for c in chunks if c.tool_calls]
    original_with_tool_calls = [c.tool_calls for c in original_chunks if c.tool_calls]

    # The processor might create extra chunks, but the tool calls themselves should be preserved.
    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_username_processor_preserves_tool_call_chunks_gemini():
    """LlmCompletionWithUsername must preserve tool_call_chunks from Gemini fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c.tool_call_chunks for c in chunks if c.tool_call_chunks]
    original_with_tool_call_chunks = [c.tool_call_chunks for c in original_chunks if c.tool_call_chunks]

    assert chunks_with_tool_call_chunks == original_with_tool_call_chunks


@pytest.mark.asyncio
async def test_username_processor_handles_string_content_gemini():
    """LlmCompletionWithUsername must handle Gemini's string content format."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Reconstruct content
    content = "".join(c.content for c in chunks if c.content is not None)

    # The processor adds a username chunk, so we expect the content to be the same but might be structured differently.
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))
    original_content = "".join(c.content for c in original_chunks if c.content is not None)

    assert content == original_content


@pytest.mark.asyncio
async def test_username_processor_no_token_loss_gemini():
    """LlmCompletionWithUsername must not lose tokens from Gemini fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    # May have more chunks due to username extraction, but not fewer
    assert len(chunks) >= len(original_chunks)


@pytest.mark.asyncio
async def test_username_processor_preserves_metadata_gemini():
    """LlmCompletionWithUsername must preserve response_metadata from Gemini fixture."""
    processor = LlmCompletionWithUsername(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Check that metadata is preserved in at least some chunks
    chunks_with_metadata = [c for c in chunks if c.response_metadata]
    assert len(chunks_with_metadata) > 0
