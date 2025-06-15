import re
from typing import AsyncIterable, List

import pytest
from langchain_core.messages import AIMessageChunk


class LlmCompletionWithUsername:
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk]):
        self.chat_completion = chat_completion
        self.buffered_tokens: List[str] = []
        self.buffering = True

    async def __aiter__(self):
        async for chunk in self.chat_completion:
            current_token = chunk.content
            tool_calls = chunk.tool_calls if hasattr(chunk, "tool_calls") else []

            if self.buffering and tool_calls:
                self.buffering = False
                full_content = "".join(self.buffered_tokens)
                match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', full_content)
                username = match.group(1) if match else None

                yield self._flush_username(chunk, username)
                remaining_content = self._extract_remaining_content(full_content)
                if remaining_content:
                    yield self._create_chunk(chunk, remaining_content)
                yield chunk
                continue

            if current_token is None:
                yield chunk
                continue

            if not self.buffering:
                yield self._create_chunk(chunk, current_token)
                continue

            self.buffered_tokens.append(current_token)

            full_content = "".join(self.buffered_tokens)

            if self._is_full_match(full_content):
                match = re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', "".join(self.buffered_tokens))
                username = match.group(1)
                yield self._flush_username(chunk, username)
                remaining_content = self._extract_remaining_content(full_content)
                if remaining_content:
                    yield self._create_chunk(chunk, remaining_content)
                self.buffering = False
                self.buffered_tokens = []
            elif not self._is_partial_match(full_content):
                yield self._flush_username(chunk, None)
                yield self._create_chunk(chunk, full_content)
                self.buffering = False
                self.buffered_tokens = []

    @staticmethod
    def _is_full_match(content: str) -> bool:
        return bool(re.match(r'^[ \n]*\*\*([^*]+)>\*\*[ \n]+', content))

    @staticmethod
    def _is_partial_match(content: str) -> bool:
        return content == '' or re.match(r'^[ \n]*\*\*[^*]*\*?\*?[ \n]?$', content)

    def _flush_username(self, chunk: AIMessageChunk, username) -> AIMessageChunk:
        return self._create_chunk(
            chunk,
            '',
            'assistant',
            username,
            tool_calls=None
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


async def create_chunks(content_list, tool_calls=None):
    """Helper to create AIMessageChunk stream from content list."""
    for i, content in enumerate(content_list):
        kwargs = {}
        if i == len(content_list) - 1 and tool_calls:
            kwargs['additional_kwargs'] = {'tool_calls': tool_calls}
        yield AIMessageChunk(content=content, **kwargs)


@pytest.mark.asyncio
async def test_extracts_username_from_markdown_pattern():
    """Allows the user to identify which assistant is responding in multi-agent conversations."""
    chunks = create_chunks(['**john>** ', 'Hello'])
    processor = LlmCompletionWithUsername(chunks)

    result = [chunk async for chunk in processor]

    # First chunk should have username
    assert result[0].name == 'john'
    assert result[0].content == ''

    # Subsequent chunks should have the actual content
    assert ''.join(chunk.content for chunk in result[1:]) == 'Hello'


@pytest.mark.asyncio
async def test_handles_streaming_username_pattern():
    """Allows the user to correctly extract username when pattern is split across chunks."""
    chunks = create_chunks(['**', 'jo', 'hn', '>', '**', ' ', 'He', 'llo'])
    processor = LlmCompletionWithUsername(chunks)

    result = [chunk async for chunk in processor]

    assert result[0].name == 'john'
    assert ''.join(chunk.content for chunk in result if chunk.content) == 'Hello'


@pytest.mark.asyncio
async def test_passes_through_content_without_username():
    """Allows the user to receive content unchanged when no username pattern is present."""
    chunks = create_chunks(['Hello', ' World'])
    processor = LlmCompletionWithUsername(chunks)

    result = [chunk async for chunk in processor]

    assert result[0].name is None
    assert ''.join(chunk.content for chunk in result if chunk.content) == 'Hello World'


@pytest.mark.asyncio
async def test_preserves_tool_calls_with_username():
    """Allows the user to receive tool calls even when username extraction occurs."""
    from taskmates.lib.matchers_ import matchers

    tool_calls = [{'id': 'call_123', 'type': 'function', 'function': {'name': 'test'}}]
    chunks = create_chunks(['**agent>** ', 'Using tool'], tool_calls=tool_calls)
    processor = LlmCompletionWithUsername(chunks)

    result = [chunk async for chunk in processor]

    # Username chunk should not have tool_calls
    assert result[0] == matchers.object_with_attrs(
        name='agent',
        content='',
        additional_kwargs={}
    )

    # Tool calls should be on the last chunk
    assert result[-1] == matchers.object_with_attrs(
        additional_kwargs=matchers.dict_containing({'tool_calls': tool_calls})
    )


@pytest.mark.asyncio
async def test_handles_whitespace_variations():
    """Allows the user to extract username with various whitespace patterns."""
    test_cases = [
        (['  **john>** Hello'], 'john', 'Hello'),
        (['\n\n**john>**\nHello'], 'john', 'Hello'),
        (['**john>**\n\nHello'], 'john', 'Hello'),
    ]

    for content_list, expected_username, expected_content in test_cases:
        chunks = create_chunks(content_list)
        processor = LlmCompletionWithUsername(chunks)
        result = [chunk async for chunk in processor]
        assert result[0].name == expected_username
        assert ''.join(chunk.content for chunk in result if chunk.content) == expected_content


@pytest.mark.asyncio
async def test_preserves_tool_call_chunks():
    """Allows the user to trigger tool calls with preserved tool_call_chunks attribute."""
    # Test chunk with all tool-related attributes
    test_chunk = AIMessageChunk(
        content="Using tool",
        tool_calls=[{'name': 'search_issues', 'args': {}, 'id': 'toolu_123', 'type': 'tool_call'}],
        tool_call_chunks=[
            {'name': 'search_issues', 'args': '', 'id': 'toolu_123', 'index': 1, 'type': 'tool_call_chunk'}],
        invalid_tool_calls=[
            {'name': None, 'args': 'invalid', 'id': None, 'error': 'parse error', 'type': 'invalid_tool_call'}],
        usage_metadata={'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30},
        response_metadata={'stop_reason': 'tool_use'},
        id='run-123'
    )

    async def chunk_generator():
        yield test_chunk

    processor = LlmCompletionWithUsername(chunk_generator())

    result = []
    async for chunk in processor:
        result.append(chunk)

    # Verify all attributes are preserved
    final_chunk = result[-1]
    assert final_chunk.tool_calls == test_chunk.tool_calls
    assert final_chunk.tool_call_chunks == test_chunk.tool_call_chunks
    assert final_chunk.invalid_tool_calls == test_chunk.invalid_tool_calls
    assert final_chunk.usage_metadata == test_chunk.usage_metadata
    assert final_chunk.response_metadata == test_chunk.response_metadata


@pytest.mark.asyncio
async def test_preserves_tool_call_chunks_with_username_extraction():
    """Allows the user to extract username while preserving tool call information."""
    chunks = [
        AIMessageChunk(content="**assistant>** ", id='run-123'),
        AIMessageChunk(
            content="I'll search",
            tool_calls=[{'name': 'search', 'args': {}, 'id': 'tool_123', 'type': 'tool_call'}],
            tool_call_chunks=[{'name': 'search', 'args': '', 'id': 'tool_123', 'index': 0, 'type': 'tool_call_chunk'}],
            response_metadata={'model': 'claude-3'},
            id='run-123'
        )
    ]

    async def chunk_generator():
        for chunk in chunks:
            yield chunk

    processor = LlmCompletionWithUsername(chunk_generator())

    result = []
    async for chunk in processor:
        result.append(chunk)

    # First chunk should have username
    assert result[0].name == 'assistant'
    assert result[0].content == ''

    # Tool call information should be preserved in subsequent chunks
    chunks_with_tool_calls = [c for c in result if c.tool_call_chunks]
    assert len(chunks_with_tool_calls) > 0
    assert chunks_with_tool_calls[0].tool_call_chunks == [
        {'name': 'search', 'args': '', 'id': 'tool_123', 'index': 0, 'type': 'tool_call_chunk'}]
