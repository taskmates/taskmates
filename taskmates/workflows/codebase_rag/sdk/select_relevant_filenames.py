from typing import List

from loguru import logger

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectableItem
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.workflows.codebase_rag.operations.batch_filenames import batch_filenames
from taskmates.workflows.codebase_rag.operations.list_files import list_files
from taskmates.workflows.codebase_rag.operations.merge_batch_results import merge_selection_results
from taskmates.workflows.codebase_rag.operations.select_files import select_files


async def select_relevant_filenames(
    question: str,
    project_root: str,
    file_pattern: str
) -> List[SelectableItem]:
    """
    List and select relevant filenames based on a question.

    Returns a list of SelectableItem objects representing the relevant files.
    """
    # Step 1: List All Files
    all_filenames: List[SelectableItem] = await list_files(
        project_root=project_root,
        file_pattern=file_pattern
    )
    logger.info(f"Found {len(all_filenames)} total files")

    # Step 2: Batch Files
    filename_batches: List[List[SelectableItem]] = await batch_filenames(
        filename_items=all_filenames,
        question=question
    )
    logger.info(f"Created {len(filename_batches)} file batches")

    # Step 3-5: Select Files in Parallel
    filename_selection_results = await runtime.map_parallel(
        operation=select_files,
        inputs_list=[
            {
                "question": question,
                "batch": batch,
                "batch_id": batch_id,
                "total_batches": len(filename_batches)
            }
            for batch_id, batch in enumerate(filename_batches)
        ]
    )

    # Merge results
    merged_filename_results = await merge_selection_results(
        batch_results=filename_selection_results,
        question=question
    )

    # Create URI to item mapping
    uri_to_item = {item['uri']: item for item in all_filenames}

    # Get selected items by URI
    selected_filename_items = [uri_to_item[uri] for uri in merged_filename_results['selected_uris'] if uri in uri_to_item]
    logger.info(f"Selected {len(selected_filename_items)} relevant files from {len(all_filenames)} total")

    return selected_filename_items
