"""
Example showing how to add transaction logging to an existing operation.
"""
from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk
import asyncio

from taskmates.core.workflow_engine.transaction_manager import runtime, TransactionManager
from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def select_relevant_chunks(question: str, chunks: List[FileChunk], threshold: float = 0.5) -> List[int]:
    """
    Example operation that selects relevant chunks based on a question.
    Demonstrates how to add transaction logging.
    """
    runtime.logger.info(f"Selecting chunks for question: {question[:50]}...")
    runtime.logger.debug(f"Total chunks to evaluate: {len(chunks)}")

    selected_ids = []

    for chunk in chunks:
        # Simulate relevance scoring
        relevance = len(set(question.lower().split()) & set(chunk['text'].lower().split())) / len(question.split())

        if relevance >= threshold:
            selected_ids.append(chunk['id'])
            runtime.logger.debug(f"Selected chunk {chunk['id']} from {chunk['path']} (relevance: {relevance:.2f})")

    runtime.logger.info(f"Selected {len(selected_ids)} out of {len(chunks)} chunks")

    if len(selected_ids) == 0:
        runtime.logger.warning("No chunks selected - consider lowering threshold")

    return selected_ids


async def demo():
    """Demonstrate the logging in action."""
    # Create some sample chunks
    chunks = [
        {"id": 0, "text": "def parse_input(text): return text.split()", "path": "parser.py", "line_start": 1, "line_end": 1, "token_count": 10},
        {"id": 1, "text": "def validate_email(email): return '@' in email", "path": "validator.py", "line_start": 1, "line_end": 1, "token_count": 10},
        {"id": 2, "text": "def format_output(data): return str(data)", "path": "formatter.py", "line_start": 1, "line_end": 1, "token_count": 10},
    ]

    # Use with transaction manager
    manager = TransactionManager(cache_dir="/tmp/demo_cache")

    with runtime.transaction_manager_context(manager):
        result = await select_relevant_chunks(
            question="How do I parse input text?",
            chunks=chunks,
            threshold=0.3
        )

    print(f"Selected chunk IDs: {result}")
    print("\nCheck logs at: /tmp/demo_cache/*/logs.txt")


if __name__ == "__main__":
    asyncio.run(demo())
