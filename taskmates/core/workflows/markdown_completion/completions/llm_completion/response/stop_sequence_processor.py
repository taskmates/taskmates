from typing import AsyncIterable, List, Optional

import pytest
from langchain_core.messages import AIMessageChunk


class StopSequenceProcessor:
    """Processes streaming LLM responses to detect and stop at configured stop sequences."""
    
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk], stop_sequences: Optional[List[str]] = None):
        self.chat_completion = chat_completion
        self.stop_sequences = stop_sequences or []
        self.accumulated_text = ""  # All text seen so far
        self.pending_chunks = []    # Chunks we're holding back
        self.pending_text = ""      # Text from pending chunks
        
    def _extract_text(self, chunk):
        """Extract text content from a chunk for stop sequence detection."""
        if chunk.content is None:
            return ""
            
        content = chunk.content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        texts.append(part.get("text", ""))
            return "".join(texts)
        return content
        
    async def __aiter__(self):
        async for chunk in self.chat_completion:
            chunk_text = self._extract_text(chunk)
            
            # If we have pending chunks, we're in the middle of checking a potential stop sequence
            if self.pending_chunks:
                self.pending_chunks.append(chunk)
                self.pending_text += chunk_text
                
                # Check if we now have a complete stop sequence
                combined_text = self.accumulated_text + self.pending_text
                for stop_seq in self.stop_sequences:
                    if stop_seq in combined_text:
                        # Stop sequence confirmed - don't yield pending chunks
                        return
                    
                # Check if pending text could still be part of a stop sequence
                could_be_stop = False
                for stop_seq in self.stop_sequences:
                    # Check if any suffix of combined text could be the start of a stop sequence
                    for i in range(len(self.accumulated_text), len(combined_text) + 1):
                        suffix = combined_text[i:]
                        if suffix and stop_seq.startswith(suffix) and suffix != stop_seq:
                            could_be_stop = True
                            break
                    if could_be_stop:
                        break
                        
                if not could_be_stop:
                    # Not a stop sequence - yield all pending chunks
                    for pending_chunk in self.pending_chunks:
                        yield pending_chunk
                    self.accumulated_text += self.pending_text
                    self.pending_chunks = []
                    self.pending_text = ""
            else:
                # Check if this chunk could start a stop sequence
                combined_text = self.accumulated_text + chunk_text
                
                # First check if we already have a complete stop sequence
                for stop_seq in self.stop_sequences:
                    if stop_seq in combined_text:
                        # Stop sequence found - don't yield this chunk
                        return
                    
                # Check if this could be the start of a stop sequence
                could_be_start = False
                for stop_seq in self.stop_sequences:
                    # Check if any suffix of combined text could start a stop sequence
                    for i in range(len(self.accumulated_text), len(combined_text) + 1):
                        suffix = combined_text[i:]
                        if suffix and stop_seq.startswith(suffix) and suffix != stop_seq:
                            could_be_start = True
                            break
                    if could_be_start:
                        break
                        
                if could_be_start:
                    # Start buffering
                    self.pending_chunks.append(chunk)
                    self.pending_text = chunk_text
                else:
                    # Safe to yield
                    yield chunk
                    self.accumulated_text += chunk_text
                    
        # Stream ended - yield any remaining pending chunks
        for pending_chunk in self.pending_chunks:
            yield pending_chunk


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
        else:
            full_content += chunk.content or ""
    
    # Use a stop sequence that exists in the content
    if "the" in full_content:
        stop_seq = "the"
        expected = full_content.split(stop_seq)[0]
        
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
            else:
                result_text += chunk.content or ""
        
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
    
    assert len(chunks) == len(original_chunks)


@pytest.mark.asyncio
async def test_stop_sequence_processor_no_token_loss_anthropic():
    """StopSequenceProcessor must not lose tokens when no stop sequence matches with Anthropic fixture."""
    processor = StopSequenceProcessor(
        load_fixture_chunks("anthropic_streaming_response.jsonl"),
        stop_sequences=["NEVER_APPEARS"]
    )
    
    chunks = await collect_chunks(processor)
    original_chunks = await collect_chunks(load_fixture_chunks("anthropic_streaming_response.jsonl"))
    
    assert len(chunks) == len(original_chunks)
