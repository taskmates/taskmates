import re
from typing import AsyncIterable, List, Optional, Union, Tuple

import pytest
from langchain_core.messages import AIMessageChunk


class StopSequenceProcessor(AsyncIterable[AIMessageChunk]):
    """
    Processes a stream of AIMessageChunk objects to detect and stop at specified stop sequences.
    This processor correctly handles stop sequences that may span across multiple chunks.
    Supports both literal strings and regex patterns for stop sequences.
    """

    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk], stop_sequences: Optional[List[str]] = None):
        self.chat_completion = chat_completion
        self.stop_sequences = stop_sequences or []
        # Compile regex patterns for stop sequences
        self.stop_patterns = []
        self.max_stop_len = 0
        
        for seq in self.stop_sequences:
            # Check if it's a regex pattern (contains regex special chars or anchors)
            if self._is_regex_pattern(seq):
                try:
                    # Use MULTILINE flag so ^ matches start of lines, not just start of string
                    pattern = re.compile(seq, re.MULTILINE)
                    self.stop_patterns.append((pattern, None))
                    # For regex patterns, use a reasonable max length
                    self.max_stop_len = max(self.max_stop_len, 100)
                except re.error:
                    # If regex compilation fails, treat as literal
                    self.stop_patterns.append((None, seq))
                    self.max_stop_len = max(self.max_stop_len, len(seq))
            else:
                # Literal string
                self.stop_patterns.append((None, seq))
                self.max_stop_len = max(self.max_stop_len, len(seq))
        
        # A buffer to hold text that might be part of a stop sequence.
        self.buffer = ""

    async def aclose(self):
        """Close the underlying stream."""
        if hasattr(self.chat_completion, 'aclose'):
            await self.chat_completion.aclose()

    def _is_regex_pattern(self, seq: str) -> bool:
        """Check if a sequence should be treated as a regex pattern."""
        # Only treat as regex if it contains anchors or specific regex constructs
        # that indicate intentional regex usage
        regex_indicators = [
            r'^',      # Start of string/line anchor
            r'$',      # End of string/line anchor  
            r'\(',     # Capturing group
            r'(?:',    # Non-capturing group
            r'(?=',    # Lookahead
            r'(?!',    # Negative lookahead
            r'(?<=',   # Lookbehind
            r'(?<!',   # Negative lookbehind
            r'\b',     # Word boundary
            r'\d',     # Digit class
            r'\w',     # Word class
            r'\s',     # Whitespace class
            r'.*',     # Any character repeated
            r'.+',     # Any character one or more
            r'.\?',    # Any character optional
        ]
        
        for indicator in regex_indicators:
            if indicator in seq:
                return True
        
        # Check for unescaped special regex chars that suggest regex intent
        # But exclude simple brackets which might be literal
        if re.search(r'(?<!\\)[*+?{}|]', seq):
            return True
            
        return False

    def _extract_text(self, chunk: AIMessageChunk) -> str:
        """Extracts text content from a chunk for stop sequence detection."""
        if not chunk.content or not isinstance(chunk.content, str):
            return ""
        return chunk.content

    def _find_stop_sequence(self, text: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Find if any stop sequence exists in the text.
        Returns (found, matched_text, index).
        """
        earliest_index = len(text)
        found_match = None
        
        for pattern, literal in self.stop_patterns:
            if pattern:
                # Regex pattern
                match = pattern.search(text)
                if match and match.start() < earliest_index:
                    earliest_index = match.start()
                    found_match = match.group()
            else:
                # Literal string
                index = text.find(literal)
                if index != -1 and index < earliest_index:
                    earliest_index = index
                    found_match = literal
        
        if found_match is not None:
            return True, found_match, earliest_index
        return False, None, None

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
            stop_found, found_seq, stop_index = self._find_stop_sequence(self.buffer)

            if stop_found:
                # A stop sequence was found. Truncate the buffer at the sequence.
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
                        id=chunk.id,
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
                    id=chunk.id,
                )
                yield new_chunk

        # After the loop, if there's anything left in the buffer, yield it.
        if self.buffer:
            # Since the stream is finished, no more text will come.
            # Check one last time for a stop sequence.
            stop_found, found_seq, stop_index = self._find_stop_sequence(self.buffer)

            if stop_found:
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
                    id=ref_chunk.id,
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


# New tests for regex support

@pytest.mark.asyncio
async def test_stop_sequence_regex_start_of_line():
    """StopSequenceProcessor must handle regex pattern for start of line."""

    async def mock_stream():
        yield AIMessageChunk(content="Some text\n")
        yield AIMessageChunk(content="###### Cell Output: stdout [cell_0]\n")
        yield AIMessageChunk(content="This should not appear")

    # Use regex pattern to match ###### at start of line
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=[r"^######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    # When using ^###### with MULTILINE, it matches at start of line, preserving the newline before it
    assert full_text == "Some text\n"


@pytest.mark.asyncio
async def test_stop_sequence_regex_start_of_text():
    """StopSequenceProcessor must handle regex pattern for start of text."""

    async def mock_stream():
        yield AIMessageChunk(content="###### Cell Output: stdout [cell_0]\n")
        yield AIMessageChunk(content="This should not appear")

    # Use regex pattern to match ###### at start of text
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=[r"^######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == ""


@pytest.mark.asyncio
async def test_stop_sequence_literal_vs_regex():
    """StopSequenceProcessor must distinguish between literal strings and regex patterns."""

    async def mock_stream():
        yield AIMessageChunk(content="Text with special chars: [test] and more")
        yield AIMessageChunk(content=" text after")

    # Literal string with regex special chars
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=["[test]"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "Text with special chars: "


@pytest.mark.asyncio
async def test_stop_sequence_mixed_literal_and_regex():
    """StopSequenceProcessor must handle mix of literal strings and regex patterns."""

    async def mock_stream():
        yield AIMessageChunk(content="Line 1\nLine 2\n")
        yield AIMessageChunk(content="###### Section\nLine 3")

    # Mix of literal and regex patterns
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=["Line 3", r"^######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "Line 1\nLine 2\n"


@pytest.mark.asyncio
async def test_stop_sequence_regex_multiline():
    """StopSequenceProcessor must handle regex patterns with multiline flag."""

    async def mock_stream():
        yield AIMessageChunk(content="First paragraph\n\n")
        yield AIMessageChunk(content="###### Cell Output\n")
        yield AIMessageChunk(content="Should not appear")

    # Regex pattern that matches ###### after newline or at start
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=[r"(?:^|\n)######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "First paragraph\n"


@pytest.mark.asyncio
async def test_stop_sequence_invalid_regex_treated_as_literal():
    """StopSequenceProcessor must treat invalid regex as literal string."""

    async def mock_stream():
        yield AIMessageChunk(content="Text with [invalid regex")
        yield AIMessageChunk(content=" more text")

    # Invalid regex should be treated as literal
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=["[invalid regex"]  # Missing closing bracket
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == "Text with "


@pytest.mark.asyncio
async def test_stop_sequence_cell_output_without_leading_newline():
    """StopSequenceProcessor must handle '###### Cell Output' at start of output."""

    async def mock_stream():
        yield AIMessageChunk(content="###### Cell Output: stdout [cell_0]\n")
        yield AIMessageChunk(content="\n\nThis should not appear")

    # Use regex pattern to match ###### at start of text or after newline
    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=[r"(?:^|\n)######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == ""


@pytest.mark.asyncio
async def test_stop_sequence_recommended_pattern_for_cell_output():
    """Test the recommended pattern for stopping at ###### Cell Output."""

    async def mock_stream():
        # Case 1: At start of text
        yield AIMessageChunk(content="###### Cell Output: stdout [cell_0]\n")
        yield AIMessageChunk(content="Should not appear")

    processor = StopSequenceProcessor(
        mock_stream(),
        stop_sequences=[r"(?:^|\n)######"]
    )
    chunks = await collect_chunks(processor)
    full_text = "".join(c.content for c in chunks if c.content)
    assert full_text == ""

    # Case 2: After newline
    async def mock_stream2():
        yield AIMessageChunk(content="Some output\n")
        yield AIMessageChunk(content="###### Cell Output: stdout [cell_0]\n")
        yield AIMessageChunk(content="Should not appear")

    processor2 = StopSequenceProcessor(
        mock_stream2(),
        stop_sequences=[r"(?:^|\n)######"]
    )
    chunks2 = await collect_chunks(processor2)
    full_text2 = "".join(c.content for c in chunks2 if c.content)
    assert full_text2 == "Some output"

    # Case 3: Not at line boundary (should not match)
    async def mock_stream3():
        yield AIMessageChunk(content="Text with ###### in middle")
        yield AIMessageChunk(content=" continues")

    processor3 = StopSequenceProcessor(
        mock_stream3(),
        stop_sequences=[r"(?:^|\n)######"]
    )
    chunks3 = await collect_chunks(processor3)
    full_text3 = "".join(c.content for c in chunks3 if c.content)
    assert full_text3 == "Text with ###### in middle continues"
