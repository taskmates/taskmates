from typing import List, TypeVar, Callable

from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens

T = TypeVar('T')


def batch_by_tokens(
        items: List[T],
        format_item: Callable[[T], str],
        max_tokens: int = 7000
) -> List[List[T]]:
    """
    Generic function to batch items based on token count.

    Args:
        items: List of items to batch
        format_item: Function that takes an item and returns formatted string for token counting
        max_tokens: Maximum tokens per batch (caller should account for any prompt overhead)

    Returns:
        List of batches, where each batch is a list of items
    """
    batches = []
    current_batch = []
    current_batch_tokens = 0

    for item in items:
        item_text = format_item(item)
        item_tokens = count_tokens(item_text)

        if current_batch_tokens + item_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = [item]
            current_batch_tokens = item_tokens
        else:
            current_batch.append(item)
            current_batch_tokens += item_tokens

    if current_batch:
        batches.append(current_batch)

    return batches
