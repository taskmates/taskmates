from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectionResult
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.workflows.codebase_rag.operations.summarize_scratchpad import summarize_scratchpad
from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def merge_selection_results(
    batch_results: List[SelectionResult],
    question: str,
    model_name: str = DEFAULT_MODEL_NAME
) -> SelectionResult:
    """
    Merge selection results from multiple batches and summarize the scratchpad.

    Works for both file selection and chunk selection - unified interface.

    Args:
        batch_results: List of SelectionResult from each batch
        question: The question being answered
        model_name: The model to use for summarization

    Returns:
        SelectionResult with merged selected_uris and summarized scratchpad
    """
    all_selected_uris = []
    all_reasoning = []

    for result in batch_results:
        all_selected_uris.extend(result['selected_uris'])
        all_reasoning.append(result['scratchpad'])

    combined_scratchpad = '\n\n'.join(all_reasoning)

    # Summarize the combined scratchpad using nested transaction
    summarized_scratchpad = await summarize_scratchpad(
        scratchpad=combined_scratchpad,
        question=question,
        model_name=model_name
    )

    return {
        'selected_uris': all_selected_uris,
        'scratchpad': summarized_scratchpad
    }
