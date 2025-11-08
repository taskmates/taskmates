from typing import List

import pytest

from taskmates.workflows.codebase_rag.operations.batch_chunks import batch_chunks
from taskmates.workflows.codebase_rag.operations.select_chunks import select_chunks
from taskmates.workflows.codebase_rag.operations.merge_batch_results import merge_selection_results
from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk, SelectionResult
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def batch_and_select_chunks(
        chunks: List[FileChunk],
        question: str,
        depth: int,
        model_name: str,
        scratchpad: str = ""
) -> SelectionResult:
    """
    Batch chunks and select relevant ones in parallel, then merge results.

    Args:
        chunks: List of chunks to process
        question: The user's question
        depth: Current depth in navigation
        model_name: Ollama model to use
        scratchpad: Current scratchpad content

    Returns:
        SelectionResult with selected IDs and updated scratchpad
    """
    batches = await batch_chunks(
        chunks=chunks,
        batch_size=50
    )

    runtime.logger.info(f"Created {len(batches)} batches at depth {depth}")

    sorted_batches = sorted(batches, key=lambda batch: batch[0]['uri'] if batch else '')

    # Process all batches in parallel
    batch_results = await runtime.map_parallel(
        operation=select_chunks,
        inputs_list=[
            {
                "question": question,
                "chunks": batch,
                "depth": depth,
                "scratchpad": scratchpad,
                "model_name": model_name
            }
            for batch in sorted_batches
        ]
    )

    # Merge results
    aggregated_results = await merge_selection_results(
        batch_results=batch_results,
        question=question,
        model_name=model_name
    )

    runtime.logger.info(f"Depth {depth} total selected chunks: {len(aggregated_results['selected_uris'])}")

    return aggregated_results
