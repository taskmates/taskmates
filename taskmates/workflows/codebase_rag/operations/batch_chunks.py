from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens


@transactional
async def batch_chunks(chunks: List[FileChunk], batch_size: int = 50, max_tokens: int = 7000) -> List[List[FileChunk]]:
    """
    Split chunks into batches based on token count to stay under prompt limit.

    Args:
        chunks: List of chunks to batch
        batch_size: Maximum number of chunks per batch (default: 50)
        max_tokens: Maximum tokens for chunk content (caller should account for prompt overhead)

    Returns:
        List of chunk batches
    """
    batches = []
    current_batch = []
    current_tokens = 0

    for chunk in chunks:
        chunk_text = f"CHUNK {chunk['id']} ({chunk['uri']}):\n{chunk['text']}\n\n"
        chunk_tokens = count_tokens(chunk_text)

        if (current_tokens + chunk_tokens > max_tokens or len(current_batch) >= batch_size) and current_batch:
            batches.append(current_batch)
            current_batch = [chunk]
            current_tokens = chunk_tokens
        else:
            current_batch.append(chunk)
            current_tokens += chunk_tokens

    if current_batch:
        batches.append(current_batch)

    return batches
