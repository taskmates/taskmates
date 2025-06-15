import json
import re
from typing import AsyncIterable, List

import pytest
from icecream import ic
from langchain_core.messages import AIMessageChunk

from taskmates import root_path


class LlmCompletionPreProcessor:
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk]):
        self.chat_completion = chat_completion
        self.name = None
        self.buffering = True

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            # Handle both OpenAI (string) and Anthropic (list) content formats
            current_token = chunk.content
            tool_calls = chunk.tool_calls if hasattr(chunk, "tool_calls") else []
            tool_call_chunks = chunk.tool_call_chunks if hasattr(chunk, "tool_call_chunks") else []

            # Always flatten content if it's a list (Anthropic format)
            def flatten_content(token):
                if isinstance(token, list):
                    texts = []
                    for part in token:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                texts.append(part.get("text", ""))
                            elif part.get("type") == "input_json_delta":
                                texts.append(part.get("partial_json", ""))
                    return "".join(texts)
                return token

            current_token = flatten_content(chunk.content)

            # If this chunk has tool_calls or invalid_tool_calls, don't include input_json_delta content as text
            invalid_tool_calls = chunk.invalid_tool_calls if hasattr(chunk, "invalid_tool_calls") else []
            if (tool_calls or invalid_tool_calls) and isinstance(chunk.content, list):
                # Only include text content, not tool arguments
                texts = []
                for part in chunk.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(part.get("text", ""))
                current_token = "".join(texts)

            # Special handling for chunks with empty content but important metadata
            if current_token is None:
                yield chunk
                continue

            # For empty content, only skip if there's nothing important in the chunk
            if current_token == "" and not tool_call_chunks and not chunk.response_metadata.get("stop_reason") and not chunk.response_metadata.get("finish_reason"):
                continue

            if not self.buffering:
                # Process all chunks, not just the first one
                if current_token:
                    # Remove carriage returns
                    current_token = current_token.replace("\r", "")
                chunk.content = current_token  # Always set, even if falsy
                yield chunk
                continue

            if current_token:
                # Remove carriage returns
                current_token = current_token.replace("\r", "")

                # Add newline for markdown elements
                if re.match(r'^[#*\->`\[\]{}]', current_token):
                    current_token = "\n" + current_token

            if current_token or tool_calls or tool_call_chunks:
                self.buffering = False
                # Set the cleaned content in the chunk
                chunk.content = current_token
                yield chunk


async def create_chunks(content_list, tool_calls=None):
    """Helper to create AIMessageChunk stream from content list."""
    for i, content in enumerate(content_list):
        kwargs = {}
        if i == 0 and tool_calls:
            kwargs['additional_kwargs'] = {'tool_calls': tool_calls}
        yield AIMessageChunk(content=content, **kwargs)


@pytest.mark.asyncio
async def test_removes_carriage_returns():
    """Allows the user to process LLM responses without carriage return characters."""
    chunks = create_chunks(['Hello\r', 'World\r\n'])
    processor = LlmCompletionPreProcessor(chunks)

    result = [chunk async for chunk in processor]

    assert [chunk.content for chunk in result if chunk.content] == ['Hello', 'World\n']


@pytest.mark.asyncio
async def test_adds_newline_before_markdown_elements():
    """Allows the user to format markdown elements properly in streamed responses."""
    test_cases = [
        (['# Title', ' content'], ['\n# Title', ' content']),
        (['* Item'], ['\n* Item']),
        (['- Item'], ['\n- Item']),
        (['```python', '\nprint("hello")'], ['\n```python', '\nprint("hello")']),
        (['> Quote', ' text'], ['\n> Quote', ' text']),
    ]

    for content_list, expected in test_cases:
        chunks = create_chunks(content_list)
        processor = LlmCompletionPreProcessor(chunks)
        result = [chunk async for chunk in processor]
        assert [chunk.content for chunk in result if chunk.content] == expected


@pytest.mark.asyncio
async def test_preserves_tool_calls():
    """Allows the user to receive tool calls from preprocessed streams."""
    from taskmates.lib.matchers_ import matchers

    tool_calls = [{'id': 'call_123', 'type': 'function', 'function': {'name': 'test'}}]
    chunks = create_chunks(['# Header'], tool_calls=tool_calls)
    processor = LlmCompletionPreProcessor(chunks)

    result = [chunk async for chunk in processor]

    assert result[0] == matchers.object_with_attrs(
        content='\n# Header',
        additional_kwargs=matchers.dict_containing({'tool_calls': tool_calls})
    )


@pytest.mark.asyncio
async def test_handles_empty_content():
    """Allows the user to process chunks with empty content - empty chunks without tool_calls are not yielded."""
    async def chunks_with_empty():
        # Create a chunk with empty content (since None is not valid)
        yield AIMessageChunk(content='')
        yield AIMessageChunk(content='Hello')

    processor = LlmCompletionPreProcessor(chunks_with_empty())

    result = [chunk async for chunk in processor]

    # Empty content chunks without tool_calls are not yielded
    assert len(result) == 1
    assert result[0].content == 'Hello'


@pytest.mark.asyncio
async def test_stops_buffering_on_first_content():
    """Allows the user to receive subsequent chunks without markdown processing after first content."""
    chunks = create_chunks(['First', '# Second', '* Third'])
    processor = LlmCompletionPreProcessor(chunks)

    result = [chunk async for chunk in processor]

    # First chunk triggers unbuffering, subsequent chunks pass through unchanged
    assert [chunk.content for chunk in result] == ['First', '# Second', '* Third']

@pytest.mark.asyncio
async def test_anthropic_tool_call_streaming_response():
    """Allows the user to process Anthropic tool call streaming responses with content as list of dicts."""
    import os
    import json
    from langchain_core.messages import AIMessageChunk

    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "../../../../../../../tests/fixtures/api-responses/anthropic_tool_call_streaming_response.jsonl"
    )
    fixture_path = os.path.normpath(fixture_path)

    with open(fixture_path, "r") as f:
        lines = f.readlines()

    # Parse each line as a dict and create AIMessageChunk
    chunks = [
        AIMessageChunk(**json.loads(line))
        for line in lines
    ]

    async def chunk_stream():
        for chunk in chunks:
            yield chunk

    processor = LlmCompletionPreProcessor(chunk_stream())
    result = [chunk async for chunk in processor]

    # The processor should only include text content, not tool arguments
    actual_content = "".join(chunk.content for chunk in result if chunk.content)

    # Should only contain the text before the tool call, not the JSON arguments
    assert actual_content == "I'll check the current weather in San Francisco for you."

    # Verify that chunks with tool_calls still have them
    chunks_with_tool_calls = [chunk for chunk in result if hasattr(chunk, "tool_calls") and chunk.tool_calls]
    assert len(chunks_with_tool_calls) > 0
