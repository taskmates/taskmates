from typing import AsyncIterable, List, Optional

import pytest
from langchain_core.messages import AIMessageChunk


class StopSequenceProcessor(AsyncIterable[AIMessageChunk]):
    """
    Processes a stream of AIMessageChunk objects to detect and stop at specified stop sequences.
    This processor correctly handles stop sequences that may span across multiple chunks.
    """

    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk], stop_sequences: Optional[List[str]] = None):
        self.chat_completion = chat_completion
        self.stop_sequences = stop_sequences or []
        # A buffer to hold text that might be part of a stop sequence.
        self.buffer = ""
        # The maximum possible length of a stop sequence, used to manage the buffer size.
        self.max_stop_len = max(len(s) for s in self.stop_sequences) if self.stop_sequences else 0

    def _extract_text(self, chunk: AIMessageChunk) -> str:
        """Extracts text content from a chunk for stop sequence detection."""
        if not chunk.content or not isinstance(chunk.content, str):
            return ""
        return chunk.content

    async def __aiter__(self) -> AsyncIterable[AIMessageChunk]:
        """
        Yields chunks from the source stream, stopping when a stop sequence is found.
        It buffers text to handle sequences that span across chunk boundaries.
        """
        if not self.stop_sequences:
            async for chunk in self.chat_completion:
                yield chunk
            return

        async for chunk in self.chat_completion:
            chunk_text = self._extract_text(chunk)
            if not chunk_text:
                yield chunk
                continue

            # Add new text to the buffer
            self.buffer += chunk_text

            # Check if any stop sequence is now in the buffer
            stop_found = False
            found_seq = None
            for seq in self.stop_sequences:
                if seq in self.buffer:
                    stop_found = True
                    found_seq = seq
                    break

            if stop_found:
                # A stop sequence was found. Truncate the buffer at the sequence.
                stop_index = self.buffer.find(found_seq)
                content_to_yield = self.buffer[:stop_index]

                if content_to_yield:
                    # Create a new chunk with the truncated content, preserving original metadata.
                    # We use the current chunk's metadata as a representative.
                    new_chunk = AIMessageChunk(
                        content=content_to_yield,
                        response_metadata=chunk.response_metadata,
                        tool_calls=chunk.tool_calls,
                        tool_call_chunks=chunk.tool_call_chunks,
                        usage_metadata=chunk.usage_metadata,
                    )
                    yield new_chunk
                # Stop the iteration.
                return

            # No stop sequence found yet. Yield content from the buffer that is safe.
            # "Safe" content is the part of the buffer that cannot be part of a future stop sequence.
            # We keep a portion of the buffer that is `max_stop_len - 1` long.
            yield_len = len(self.buffer) - self.max_stop_len + 1
            if yield_len > 0:
                content_to_yield = self.buffer[:yield_len]
                self.buffer = self.buffer[yield_len:]

                # Create a new chunk with the safe content.
                new_chunk = AIMessageChunk(
                    content=content_to_yield,
                    response_metadata=chunk.response_metadata,
                    tool_calls=chunk.tool_calls,
                    tool_call_chunks=chunk.tool_call_chunks,
                    usage_metadata=chunk.usage_metadata,
                )
                yield new_chunk

        # After the loop, if there's anything left in the buffer, yield it.
        if self.buffer:
            # Since the stream is finished, no more text will come.
            # Check one last time for a stop sequence.
            stop_found = False
            found_seq = None
            for seq in self.stop_sequences:
                if seq in self.buffer:
                    stop_found = True
                    found_seq = seq
                    break

            if stop_found:
                stop_index = self.buffer.find(found_seq)
                content_to_yield = self.buffer[:stop_index]
            else:
                content_to_yield = self.buffer

            if content_to_yield:
                # We need a reference chunk for metadata. If the last chunk exists, use it.
                # If the stream was empty, we can't create a chunk.
                try:
                    ref_chunk = chunk
                except NameError:
                    ref_chunk = AIMessageChunk(content="")  # Fallback

                final_chunk = AIMessageChunk(
                    content=content_to_yield,
                    response_metadata=ref_chunk.response_metadata,
                    tool_calls=ref_chunk.tool_calls,
                    tool_call_chunks=ref_chunk.tool_call_chunks,
                    usage_metadata=ref_chunk.usage_metadata,
                )
                yield final_chunk


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
                data = json.loads(line)
                # Gemini tool call chunks can be complex, handle them carefully
                if 'tool_calls' in data and data['tool_calls'] is None:
                    del data['tool_calls']
                yield AIMessageChunk(**data)
        else:
            data = json.load(f)
            yield AIMessageChunk(**data)


async def collect_chunks(async_iter):
    """Collect all chunks from an async iterator."""
    chunks = []
    async for chunk in async_iter:
        chunks.append(chunk)
    return chunks


# Invariant tests for StopSequenceProcessor

@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_tool_calls_openai():
    """StopSequenceProcessor must preserve tool_calls from OpenAI fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_chunks = await collect_chunks(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_tool_calls_anthropic():
    """StopSequenceProcessor must preserve tool_calls from Anthropic fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_tool_call_streaming_response.jsonl"))
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_tool_call_chunks_openai():
    """StopSequenceProcessor must preserve tool_call_chunks from OpenAI fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c for c in chunks if c.tool_call_chunks]
    original_chunks = await collect_chunks(load_fixture_chunks("openai_tool_call_streaming_response.jsonl"))
    original_with_tool_call_chunks = [c for c in original_chunks if c.tool_call_chunks]

    assert chunks_with_tool_call_chunks == original_with_tool_call_chunks


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_annotations_openai_web_search():
    """StopSequenceProcessor must preserve annotations from OpenAI web search fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_web_search_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_web_search_tool_call_streaming_response.jsonl"))

    # Check that all chunks match exactly (including any annotations in content)
    assert chunks == original_chunks


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_metadata_openai():
    """StopSequenceProcessor must preserve response_metadata from OpenAI fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_metadata_anthropic():
    """StopSequenceProcessor must preserve response_metadata from Anthropic fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("anthropic_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_stop_sequence_processor_stops_at_sequence_openai():
    """StopSequenceProcessor must stop at configured stop sequence with OpenAI fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_streaming_response.jsonl"),
        stop_sequences=[", 3"]  # Should stop before "3"
    )

    chunks = await collect_chunks(processor)

    # Reconstruct the full text
    full_text = "".join(c.content for c in chunks if c.content)

    assert full_text == "1, 2"


@pytest.mark.asyncio
async def test_stop_sequence_processor_stops_at_sequence_anthropic():
    """StopSequenceProcessor must stop at configured stop sequence with Anthropic fixture."""
    # First, let's see what content is in the anthropic fixture
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    # Find a suitable stop sequence from the actual content
    full_content = ""
    for chunk in original_chunks:
        if isinstance(chunk.content, list):
            for part in chunk.content:
                if isinstance(part, dict) and part.get("type") == "text":
                    full_content += part.get("text", "")
        elif chunk.content:
            full_content += chunk.content

    # Use a stop sequence that exists in the content
    if "the" in full_content:
        stop_seq = "the"
        expected = full_content.split(stop_seq, 1)[0]

        processor = StopSequenceProcessor(
            load_fixture_chunks("anthropic_streaming_response.jsonl"),
            stop_sequences=[stop_seq]
        )

        chunks = await collect_chunks(processor)

        # Reconstruct the text
        result_text = ""
        for chunk in chunks:
            if isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        result_text += part.get("text", "")
            elif chunk.content:
                result_text += chunk.content

        assert result_text == expected


@pytest.mark.asyncio
async def test_stop_sequence_processor_no_token_loss_openai():
    """StopSequenceProcessor must not lose tokens when no stop sequence matches with OpenAI fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("openai_streaming_response.jsonl"),
        stop_sequences=["NEVER_APPEARS"]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("openai_streaming_response.jsonl"))

    original_text = "".join(c.content for c in original_chunks if c.content)
    processed_text = "".join(c.content for c in chunks if c.content)

    assert processed_text == original_text


@pytest.mark.asyncio
async def test_stop_sequence_processor_no_token_loss_anthropic():
    """StopSequenceProcessor must not lose tokens when no stop sequence matches with Anthropic fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("anthropic_streaming_response.jsonl"),
        stop_sequences=["NEVER_APPEARS"]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))

    original_text = ""
    for chunk in original_chunks:
        if isinstance(chunk.content, list):
            for part in chunk.content:
                if isinstance(part, dict) and part.get("type") == "text":
                    original_text += part.get("text", "")
        elif chunk.content:
            original_text += chunk.content

    processed_text = ""
    for chunk in chunks:
        if isinstance(chunk.content, list):
            for part in chunk.content:
                if isinstance(part, dict) and part.get("type") == "text":
                    processed_text += part.get("text", "")
        elif chunk.content:
            processed_text += chunk.content

    assert processed_text == original_text


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_tool_calls_gemini():
    """StopSequenceProcessor must preserve tool_calls from Gemini fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)

    # Find chunks with tool_calls
    chunks_with_tool_calls = [c for c in chunks if c.tool_calls]
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))
    original_with_tool_calls = [c for c in original_chunks if c.tool_calls]

    assert chunks_with_tool_calls == original_with_tool_calls


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_tool_call_chunks_gemini():
    """StopSequenceProcessor must preserve tool_call_chunks from Gemini fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)

    # Find chunks with tool_call_chunks
    chunks_with_tool_call_chunks = [c for c in chunks if c.tool_call_chunks]
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_tool_call_streaming_response.jsonl"))
    original_with_tool_call_chunks = [c for c in original_chunks if c.tool_call_chunks]

    assert chunks_with_tool_call_chunks == original_with_tool_call_chunks


@pytest.mark.asyncio
async def test_stop_sequence_processor_preserves_metadata_gemini():
    """StopSequenceProcessor must preserve response_metadata from Gemini fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("gemini_streaming_response.jsonl"),
        stop_sequences=[]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    # All metadata should be preserved
    assert [c.response_metadata for c in chunks] == [c.response_metadata for c in original_chunks]


@pytest.mark.asyncio
async def test_stop_sequence_processor_stops_at_sequence_gemini():
    """StopSequenceProcessor must stop at configured stop sequence with Gemini fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("gemini_streaming_response.jsonl"),
        stop_sequences=["4\n5"]  # Should stop before "4\n5"
    )

    chunks = await collect_chunks(processor)

    # Reconstruct the full text
    full_text = "".join(c.content for c in chunks if c.content)

    assert full_text == "1\n2\n3\n"


@pytest.mark.asyncio
async def test_stop_sequence_processor_no_token_loss_gemini():
    """StopSequenceProcessor must not lose tokens when no stop sequence matches with Gemini fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("gemini_streaming_response.jsonl"),
        stop_sequences=["NEVER_APPEARS"]
    )

    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("gemini_streaming_response.jsonl"))

    original_text = "".join(c.content for c in original_chunks if c.content)
    processed_text = "".join(c.content for c in chunks if c.content)

    assert processed_text == original_text


@pytest.mark.asyncio
async def test_stop_sequence_spanning_chunks():
    """StopSequenceProcessor must handle stop sequences that span across two chunks."""

    async def mock_stream():
        yield AIMessageChunk(content="Hello, this is chunk 1, part ")
        yield AIMessageChunk(content="1. And this is chunk 2, part 2.")

    processor = StopSequenceProcessor(mock_stream(), stop_sequences=["part 1. And"])
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "Hello, this is chunk 1, "


@pytest.mark.asyncio
async def test_stop_sequence_cell_output_spanning_chunks():
    """StopSequenceProcessor must handle '###### Cell Output' stop sequence split across two chunks."""

    async def mock_stream():
        yield AIMessageChunk(content="This is output before the cell marker\n#####")
        yield AIMessageChunk(content="# Cell Output\nAnd this should not appear.")

    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=["###### Cell Output"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "This is output before the cell marker\n"
