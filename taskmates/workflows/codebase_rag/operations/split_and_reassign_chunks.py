from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk
from taskmates.workflows.codebase_rag.operations.split_chunk_by_tokens import split_chunk_by_tokens
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflow_engine.transaction_manager import runtime


@transactional
async def split_and_reassign_chunks(
        selected_chunks: List[FileChunk],
        min_chunk_tokens: int
) -> List[FileChunk]:
    """
    Split selected chunks into smaller sub-chunks and reassign IDs.

    URIs are updated to reflect the new line ranges.

    Args:
        selected_chunks: List of chunks to split
        min_chunk_tokens: Minimum tokens per chunk

    Returns:
        List of smaller chunks with reassigned IDs
    """
    next_level_chunks = []
    next_chunk_id = 0

    for chunk in selected_chunks:
        sub_chunks = await split_chunk_by_tokens(
            chunk=chunk,
            min_tokens=min_chunk_tokens
        )

        if len(sub_chunks) > 1:
            # Multiple sub-chunks created
            for sub_chunk in sub_chunks:
                sub_chunk['id'] = next_chunk_id
                next_level_chunks.append(sub_chunk)
                next_chunk_id += 1
        else:
            # No split occurred, keep original chunk
            chunk['id'] = next_chunk_id
            next_level_chunks.append(chunk)
            next_chunk_id += 1

    runtime.logger.info(f"Created {len(next_level_chunks)} next-level chunks")

    return next_level_chunks
