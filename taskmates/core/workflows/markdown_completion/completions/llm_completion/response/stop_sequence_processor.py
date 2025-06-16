from typing import AsyncIterable, List, Optional

import pytest
from langchain_core.messages import AIMessageChunk


class StopSequenceProcessor:
    """Processes streaming LLM responses to detect and stop at configured stop sequences."""
    
    def __init__(self, chat_completion: AsyncIterable[AIMessageChunk], stop_sequences: Optional[List[str]] = None):
        self.chat_completion = chat_completion
        self.stop_sequences = stop_sequences or []
        self.buffer = ""
        self.stopped = False
        self.yielded_length = 0  # Track how much content we've already yielded
        
    async def __aiter__(self):
        last_chunk_metadata = None
        
        async for chunk in self.chat_completion:
            last_chunk_metadata = chunk
            
            if self.stopped:
                # Don't yield any more chunks after stop sequence detected
                break
                
            # Handle chunks with no content or empty content
            if chunk.content is None or chunk.content == "":
                yield chunk
                continue
                
            # Add current content to buffer
            self.buffer += chunk.content
            
            # Check if any stop sequence is present in the buffer
            stop_index = -1
            
            for stop_seq in self.stop_sequences:
                index = self.buffer.find(stop_seq)
                if index != -1 and (stop_index == -1 or index < stop_index):
                    stop_index = index
                    
            if stop_index != -1:
                # Stop sequence found
                self.stopped = True
                
                # Yield any content before the stop sequence that hasn't been yielded yet
                content_to_yield = self.buffer[self.yielded_length:stop_index]
                if content_to_yield:
                    yield self._create_chunk(chunk, content_to_yield)
                break
            else:
                # No stop sequence found yet
                # Calculate how much we can safely yield
                # We need to hold back enough characters to detect any stop sequence
                max_stop_len = max(len(seq) for seq in self.stop_sequences) if self.stop_sequences else 0
                
                if len(self.buffer) > max_stop_len:
                    # We can safely yield content up to buffer_len - max_stop_len
                    safe_yield_end = len(self.buffer) - max_stop_len
                    content_to_yield = self.buffer[self.yielded_length:safe_yield_end]
                    
                    if content_to_yield:
                        self.yielded_length = safe_yield_end
                        yield self._create_chunk(chunk, content_to_yield)
                        
        # Stream ended, yield any remaining buffered content
        if not self.stopped and self.yielded_length < len(self.buffer) and last_chunk_metadata:
            remaining_content = self.buffer[self.yielded_length:]
            if remaining_content:
                yield self._create_chunk(last_chunk_metadata, remaining_content)
    
    def _create_chunk(self, original_chunk: AIMessageChunk, content: str) -> AIMessageChunk:
        """Create a new chunk with the given content, preserving metadata from the original."""
        return AIMessageChunk(
            content=content,
            response_metadata=getattr(original_chunk, "response_metadata", {}),
            additional_kwargs=getattr(original_chunk, "additional_kwargs", {}),
            name=getattr(original_chunk, "name", None),
            id=getattr(original_chunk, "id", None),
            tool_calls=getattr(original_chunk, "tool_calls", []),
            tool_call_chunks=getattr(original_chunk, "tool_call_chunks", []),
            invalid_tool_calls=getattr(original_chunk, "invalid_tool_calls", []),
            usage_metadata=getattr(original_chunk, "usage_metadata", None),
        )


async def create_chunks(content_list):
    """Helper to create AIMessageChunk stream from content list."""
    for content in content_list:
        yield AIMessageChunk(content=content)


@pytest.mark.asyncio
async def test_stops_at_stop_sequence():
    """Allows the user to stop generation at specified stop sequences."""
    # Realistic token-by-token streaming
    chunks = create_chunks(['Hello', ' world', '\n', '#', '#', '#', '#', '#', '#', ' Cell', ' Output'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello world'


@pytest.mark.asyncio
async def test_handles_stop_sequence_across_chunks():
    """Allows the user to detect stop sequences split across multiple chunks."""
    # Stop sequence split across multiple single-character chunks
    chunks = create_chunks(['Hello', ' world', '\n', '#', '#', '#', '#', '#', '#', ' Cell', ' Output'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello world'


@pytest.mark.asyncio
async def test_handles_multiple_stop_sequences():
    """Allows the user to specify multiple stop sequences."""
    # Token-by-token with username stop sequence
    chunks = create_chunks(['Hello', '\n', '**', 'user', '>', '**', ' ', 'more', ' text'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######', '\n**user>** '])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello'


@pytest.mark.asyncio
async def test_handles_no_stop_sequences():
    """Allows the user to process streams without stop sequences."""
    chunks = create_chunks(['Hello', ' world', '!'])
    processor = StopSequenceProcessor(chunks, stop_sequences=[])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello world!'


@pytest.mark.asyncio
async def test_preserves_chunk_metadata():
    """Allows the user to receive chunks with preserved metadata."""
    from taskmates.lib.matchers_ import matchers
    
    async def chunks_with_metadata():
        yield AIMessageChunk(
            content='Hello',
            response_metadata={'model': 'test'},
            id='chunk-1'
        )
        yield AIMessageChunk(
            content=' world',
            response_metadata={'model': 'test'},
            id='chunk-2'
        )
    
    processor = StopSequenceProcessor(chunks_with_metadata(), stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    assert all(chunk.response_metadata.get('model') == 'test' for chunk in result)
    assert all(chunk.id is not None for chunk in result)


@pytest.mark.asyncio
async def test_handles_partial_stop_sequence_at_end():
    """Allows the user to receive all content when stream ends with partial stop sequence."""
    # Partial stop sequence at end
    chunks = create_chunks(['Hello', ' world', '\n', '#', '#', '#'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello world\n###'


@pytest.mark.asyncio
async def test_buffers_potential_stop_sequences():
    """Ensures the processor correctly buffers content that might be part of a stop sequence."""
    # Each character as a separate token
    chunks = create_chunks(['Hello', '\n', '#', '#', '#', '#', '#', '#', ' done'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    # Should stop before ' done'
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello'


@pytest.mark.asyncio
async def test_handles_false_start_stop_sequence():
    """Allows the user to continue when partial match doesn't complete."""
    # Start of stop sequence but doesn't complete
    chunks = create_chunks(['Hello', '\n', '#', '#', ' not', ' a', ' stop'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello\n## not a stop'


@pytest.mark.asyncio
async def test_handles_overlapping_stop_sequences():
    """Allows the user to handle overlapping stop sequences correctly."""
    # Test with overlapping sequences where shorter one appears first
    chunks = create_chunks(['Hello', '\n', '**', 'user', '>', '**', ' ', 'text'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n**user>**', '\n**user>** '])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == 'Hello'


@pytest.mark.asyncio
async def test_handles_stop_sequence_at_start():
    """Allows the user to handle stop sequence appearing at the very start."""
    chunks = create_chunks(['\n', '#', '#', '#', '#', '#', '#', ' Output'])
    processor = StopSequenceProcessor(chunks, stop_sequences=['\n######'])
    
    result = [chunk async for chunk in processor]
    
    content = ''.join(chunk.content for chunk in result if chunk.content)
    assert content == ''
