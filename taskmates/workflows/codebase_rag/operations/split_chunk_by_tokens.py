from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens
from taskmates.workflows.codebase_rag.utils.parse_uri import parse_chunk_uri


@transactional
async def split_chunk_by_tokens(chunk: FileChunk, min_tokens: int) -> List[FileChunk]:
    """
    Split a chunk into smaller chunks based on token count, respecting line boundaries.

    Updates URIs to reflect the new line ranges.

    Args:
        chunk: The chunk to split
        min_tokens: Minimum tokens per sub-chunk

    Returns:
        List of sub-chunks with updated URIs
    """
    path, line_start, line_end = parse_chunk_uri(chunk['uri'])
    lines = chunk['text'].split('\n')

    sub_chunks: List[FileChunk] = []
    current_lines: List[str] = []
    current_tokens = 0
    current_line_start = line_start

    for i, line in enumerate(lines):
        line_tokens = count_tokens(line)

        if current_tokens + line_tokens > min_tokens * 2 and current_tokens >= min_tokens:
            sub_chunk_text = '\n'.join(current_lines)
            sub_chunk_line_end = current_line_start + len(current_lines) - 1

            sub_chunks.append({
                'id': len(sub_chunks),
                'uri': f"{path}:{current_line_start}-{sub_chunk_line_end}",
                'text': sub_chunk_text,
                'token_count': current_tokens
            })

            current_lines = [line]
            current_tokens = line_tokens
            current_line_start = line_start + i
        else:
            current_lines.append(line)
            current_tokens += line_tokens

    if current_lines:
        sub_chunk_text = '\n'.join(current_lines)
        sub_chunk_line_end = current_line_start + len(current_lines) - 1

        sub_chunks.append({
            'id': len(sub_chunks),
            'uri': f"{path}:{current_line_start}-{sub_chunk_line_end}",
            'text': sub_chunk_text,
            'token_count': current_tokens
        })

    return sub_chunks
