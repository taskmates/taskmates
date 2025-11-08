from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectionResult, SelectableItem
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.workflows.codebase_rag.operations.select_files_batch import select_files_batch
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def select_files(
        question: str,
        batch: List[SelectableItem],
        batch_id: int,
        total_batches: int,
        model_name: str = DEFAULT_MODEL_NAME
) -> SelectionResult:
    """
    Select relevant files from a single batch.
    This is a wrapper around select_files_batch that can be cached by transaction_manager.

    Args:
        question: The user's question
        batch: Batch of file items to evaluate
        batch_id: Index of this batch
        total_batches: Total number of batches
        model_name: Ollama model to use

    Returns:
        SelectionResult with selected file IDs and reasoning
    """
    runtime.logger.info(f"Selecting files from batch {batch_id + 1}/{total_batches}")

    return await select_files_batch(
        question=question,
        batch=batch,
        batch_id=batch_id,
        total_batches=total_batches,
        model_name=model_name
    )
