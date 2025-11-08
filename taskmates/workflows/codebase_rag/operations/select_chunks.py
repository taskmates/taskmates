from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk, SelectionResult
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.workflows.codebase_rag.operations.select_chunks_batch import select_chunks_batch
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def select_chunks(
        question: str,
        chunks: List[FileChunk],
        depth: int,
        scratchpad: str = "",
        model_name: str = DEFAULT_MODEL_NAME
) -> SelectionResult:
    """
    Ask the model which chunks contain information relevant to the question.

    Args:
        question: The user's question
        chunks: List of chunks to evaluate
        depth: Current depth in navigation
        scratchpad: Current scratchpad content
        model_name: Ollama model to use

    Returns:
        SelectionResult with selected IDs and updated scratchpad
    """
    runtime.logger.info(f"\n==== ROUTING AT DEPTH {depth} ====")
    runtime.logger.info(f"Evaluating {len(chunks)} chunks for relevance")

    result = await select_chunks_batch(question, chunks, depth, 0, model_name)

    scratchpad_entry = f"DEPTH {depth} REASONING:\n{result['scratchpad']}"
    if scratchpad:
        new_scratchpad = scratchpad + "\n\n" + scratchpad_entry
    else:
        new_scratchpad = scratchpad_entry

    return {
        'selected_uris': result['selected_uris'],
        'scratchpad': new_scratchpad
    }
