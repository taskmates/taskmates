from typing import List

from loguru import logger

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectableItem, FileChunk
from taskmates.workflows.codebase_rag.utils.filter_selected_chunks import filter_selected_chunks
from taskmates.workflows.codebase_rag.operations.fit_chunks_to_tokens import fit_chunks_to_tokens
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.workflows.codebase_rag.operations.batch_chunks import batch_chunks
from taskmates.workflows.codebase_rag.operations.load_files import load_files
from taskmates.workflows.codebase_rag.operations.merge_batch_results import merge_selection_results
from taskmates.workflows.codebase_rag.operations.select_chunks import select_chunks


async def select_relevant_chunks(
    question: str,
    selected_filenames: List[SelectableItem],
    project_root: str,
    file_pattern: str
) -> tuple[List[FileChunk], str]:
    """
    Get relevant code chunks from selected filenames.

    Returns a tuple of (final_snippets, final_scratchpad).
    """
    # Step 6: Load Selected Files
    content_chunks = await load_files(
        project_root=project_root,
        file_pattern=file_pattern,
        selected_items=selected_filenames
    )
    logger.info(f"Loaded {len(content_chunks)} file chunks from selected files")

    # Step 7: Batch Chunks
    chunk_batches: List[List[FileChunk]] = await batch_chunks(
        chunks=content_chunks
    )
    logger.info(f"Created {len(chunk_batches)} batches")

    # Step 8-10: Select Chunks from Batches (Depth 0)
    depth = 0
    sorted_batches = sorted(chunk_batches, key=lambda batch: batch[0]['uri'] if batch else '')

    # Process all batches in parallel
    batch_results = await runtime.map_parallel(
        operation=select_chunks,
        inputs_list=[
            {
                "question": question,
                "chunks": batch,
                "depth": depth,
                "scratchpad": ""
            }
            for batch in sorted_batches
        ]
    )

    # Aggregate results
    aggregated_results = await merge_selection_results(
        batch_results=batch_results,
        question=question
    )
    logger.info(f"Processed {len(sorted_batches)} batches, selected {len(aggregated_results['selected_uris'])} chunks")

    # Step 11: Filter Selected Chunks
    selected_chunks = filter_selected_chunks(
        chunks=content_chunks,
        selected_uris=aggregated_results['selected_uris']
    )
    logger.info(f"Filtered to {len(selected_chunks)} selected chunks")

    # Step 12-14: Navigate to snippets that fit within token budget
    result = await fit_chunks_to_tokens(
        initial_chunks=selected_chunks,
        initial_scratchpad=aggregated_results['scratchpad'],
        question=question,
        initial_depth=depth
    )

    final_snippets = result['chunks']
    final_scratchpad = result['scratchpad']

    logger.info(f"Navigation complete - final snippets: {len(final_snippets)}")

    return final_snippets, final_scratchpad
