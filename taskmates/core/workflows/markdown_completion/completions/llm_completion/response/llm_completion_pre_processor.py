import re
from typing import AsyncIterable

import pytest
from langchain_core.messages import AIMessageChunk


class LlmCompletionPreProcessor:
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk]):
        self.chat_completion = chat_completion
        self.first_chunk = True

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            # Extract annotations if present
            annotations = []
            if isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, dict) and "annotations" in part:
                        annotations.extend(part.get("annotations", []))

            # Store annotations as a custom attribute
            if annotations:
                chunk.annotations = annotations

            # Only modify string content
            if isinstance(chunk.content, str) and chunk.content:
                # Remove carriage returns
                chunk.content = chunk.content.replace("\r", "")

                # Add newline for markdown elements on first chunk with content
                if self.first_chunk and re.match(r'^[#*\->`\[\]{}]', chunk.content):
                    chunk.content = "\n" + chunk.content
                    self.first_chunk = False
                elif chunk.content:  # Has content but not markdown
                    self.first_chunk = False

            yield chunk


# Test helpers
import json
import os


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


# Invariant tests for LlmCompletionPreProcessor

@pytest.mark.asyncio
async def test_preprocessor_preserves_tool_calls_openai():
    """LlmCompletionPreProcessor must preserve tool_calls from OpenAI fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_preprocessor_preserves_tool_calls_anthropic():
    """LlmCompletionPreProcessor must preserve tool_calls from Anthropic fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_preprocessor_preserves_tool_call_chunks_openai():
    """LlmCompletionPreProcessor must preserve tool_call_chunks from OpenAI fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c for c in chunks if c.tool_call_chunks]
    original_with_tool_call_chunks = [c for c in original_chunks if c.tool_call_chunks]

    assert chunks_with_tool_call_chunks == original_with_tool_call_chunks


@pytest.mark.asyncio
async def test_preprocessor_preserves_content_structure_anthropic():
    """LlmCompletionPreProcessor must preserve Anthropic's list content structure."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # Check that list content remains as list
    for chunk, original in zip(chunks, original_chunks):
        if isinstance(original.content, list):
            assert isinstance(chunk.content, list)
            assert chunk.content == original.content


@pytest.mark.asyncio
async def test_preprocessor_preserves_content_structure_openai():
    """LlmCompletionPreProcessor must preserve OpenAI's string content structure."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    # Check that string content remains as string
    for chunk, original in zip(chunks, original_chunks):
        if isinstance(original.content, str):
            assert isinstance(chunk.content, str)


@pytest.mark.asyncio
async def test_preprocessor_extracts_annotations_openai_web_search():
    """LlmCompletionPreProcessor must extract annotations from OpenAI web search fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_web_search_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)

    # Check that annotations were extracted
    chunks_with_annotations = [c for c in chunks if hasattr(c, 'annotations') and c.annotations]

    assert len(chunks_with_annotations) > 0


@pytest.mark.asyncio
async def test_preprocessor_removes_carriage_returns():
    """LlmCompletionPreProcessor must remove carriage returns from string content."""

    # Create a custom chunk with carriage returns
    async def chunks_with_cr():
        yield AIMessageChunk(content="Hello\rWorld\r\n")

    processor = LlmCompletionPreProcessor(chunks_with_cr())
    chunks = await collect_chunks(processor)

    assert chunks[0].content == "HelloWorld\n"


@pytest.mark.asyncio
async def test_preprocessor_adds_newline_before_markdown():
    """LlmCompletionPreProcessor must add newline before markdown elements in string content."""

    # Create chunks with markdown elements
    async def markdown_chunks():
        yield AIMessageChunk(content="# Title")
        yield AIMessageChunk(content="* Item")
        yield AIMessageChunk(content="Regular text")

    processor = LlmCompletionPreProcessor(markdown_chunks())
    chunks = await collect_chunks(processor)

    assert chunks[0].content == "\n# Title"
    assert chunks[1].content == "* Item"  # Not first chunk, no newline added
    assert chunks[2].content == "Regular text"  # No markdown element


@pytest.mark.asyncio
async def test_preprocessor_preserves_metadata_openai():
    """LlmCompletionPreProcessor must preserve response_metadata from OpenAI fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_preprocessor_preserves_metadata_anthropic():
    """LlmCompletionPreProcessor must preserve response_metadata from Anthropic fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_preprocessor_no_token_loss_openai():
    """LlmCompletionPreProcessor must not lose any tokens from OpenAI fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("openai_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    assert len(chunks) == len(original_chunks)


@pytest.mark.asyncio
async def test_preprocessor_no_token_loss_anthropic():
    """LlmCompletionPreProcessor must not lose any tokens from Anthropic fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    assert len(chunks) == len(original_chunks)


@pytest.mark.asyncio
async def test_preprocessor_preserves_tool_calls_gemini():
    """LlmCompletionPreProcessor must preserve tool_calls from Gemini fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_preprocessor_preserves_tool_call_chunks_gemini():
    """LlmCompletionPreProcessor must preserve tool_call_chunks from Gemini fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c for c in chunks if c.tool_call_chunks]
    original_with_tool_call_chunks = [c for c in original_chunks if c.tool_call_chunks]

    assert chunks_with_tool_call_chunks == original_with_tool_call_chunks


@pytest.mark.asyncio
async def test_preprocessor_preserves_content_structure_gemini():
    """LlmCompletionPreProcessor must preserve Gemini's string content structure."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    # Check that string content remains as string
    for chunk, original in zip(chunks, original_chunks):
        if isinstance(original.content, str):
            assert isinstance(chunk.content, str)


@pytest.mark.asyncio
async def test_preprocessor_preserves_metadata_gemini():
    """LlmCompletionPreProcessor must preserve response_metadata from Gemini fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_preprocessor_no_token_loss_gemini():
    """LlmCompletionPreProcessor must not lose any tokens from Gemini fixture."""
    processor = LlmCompletionPreProcessor(load_fixture_chunks("gemini_streaming_response.jsonl"))

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    assert len(chunks) == len(original_chunks)
