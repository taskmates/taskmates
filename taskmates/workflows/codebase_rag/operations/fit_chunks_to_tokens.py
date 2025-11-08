from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.workflows.codebase_rag.utils.filter_selected_chunks import filter_selected_chunks
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.operations.batch_and_select_chunks import batch_and_select_chunks
from taskmates.workflows.codebase_rag.operations.split_and_reassign_chunks import split_and_reassign_chunks
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens


def format_code_snippet(chunk: FileChunk) -> str:
    """Standard format for code snippets in prompts."""
    return f"CODE SNIPPET {chunk['uri']}:\n{chunk['text']}\n\n"


# TODO: proper typed return type instead of dict
@transactional
async def fit_chunks_to_tokens(
        initial_chunks: List[FileChunk],
        initial_scratchpad: str,
        question: str,
        initial_depth: int = 0,
        model_name: str = DEFAULT_MODEL_NAME,
        max_tokens: int = 7000,
        min_chunk_tokens: int = 500
) -> dict:
    """
    Iteratively split and refine chunks until they fit within token budget.

    This function implements the core principle: NEVER LOSE DATA - ALWAYS LET THE LLM DECIDE.
    If selected chunks don't fit in the token budget, we split them smaller and ask the LLM
    to select again. We keep iterating until the LLM's selection fits.

    The loop is sequential across depths because:
    1. Each depth's scratchpad depends on the previous depth's reasoning
    2. We stop as soon as we find a depth that fits (no need to go deeper)

    However, within each depth, batches are processed in parallel for efficiency.

    Args:
        initial_chunks: Starting chunks to navigate
        initial_scratchpad: Starting scratchpad content
        question: User's question
        model_name: LLM model to use
        max_tokens: Maximum tokens allowed for answer generation
        initial_depth: Starting depth level (default: 0)
        min_chunk_tokens: Minimum tokens per chunk at depth 0 (default: 500)

    Returns:
        Dict with 'chunks' and 'scratchpad' keys that fit within token budget
    """
    current_chunks = initial_chunks
    current_scratchpad = initial_scratchpad
    depth = initial_depth

    total_tokens = sum(count_tokens(format_code_snippet(c)) for c in current_chunks)

    while total_tokens > max_tokens:
        runtime.logger.info(
            f"Chunks don't fit ({total_tokens}/{max_tokens} tokens) - "
            f"splitting to depth {depth + 1}"
        )

        depth += 1

        next_level_chunks = await split_and_reassign_chunks(
            selected_chunks=current_chunks,
            min_chunk_tokens=min_chunk_tokens // (2 ** depth)
        )

        runtime.logger.info(f"Split into {len(next_level_chunks)} smaller chunks at depth {depth}")

        next_results = await batch_and_select_chunks(
            chunks=next_level_chunks,
            question=question,
            depth=depth,
            model_name=model_name,
            scratchpad=current_scratchpad
        )

        current_chunks = filter_selected_chunks(
            chunks=next_level_chunks,
            selected_uris=next_results['selected_uris']
        )
        current_scratchpad = next_results['scratchpad']

        total_tokens = sum(count_tokens(format_code_snippet(c)) for c in current_chunks)

        runtime.logger.info(
            f"Depth {depth}: {len(current_chunks)} chunks, {total_tokens} tokens"
        )

    runtime.logger.info(
        f"Final: {len(current_chunks)} chunks fit in {total_tokens}/{max_tokens} tokens"
    )

    return {
        'chunks': current_chunks,
        'scratchpad': current_scratchpad
    }
