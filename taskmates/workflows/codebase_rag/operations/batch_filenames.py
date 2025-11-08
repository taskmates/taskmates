from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectableItem
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.utils.batch_by_tokens import batch_by_tokens
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens


@transactional
async def batch_filenames(
        filename_items: List[SelectableItem],
        question: str,
        max_tokens: int = 7000
) -> List[List[SelectableItem]]:
    """
    Batch file items based on token count to stay under prompt limit.

    Args:
        filename_items: List of SelectableItems (files) to batch
        question: The user's question (for token calculation)
        max_tokens: Maximum tokens per batch (default: 7000)

    Returns:
        List of batches, where each batch is a list of SelectableItems
    """
    batches = batch_by_tokens(
        items=filename_items,
        format_item=lambda item: f"{item['id']}. {item['uri']}\n",
        max_tokens=max_tokens
    )

    return batches
