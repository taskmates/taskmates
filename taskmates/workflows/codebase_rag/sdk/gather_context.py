from taskmates.workflows.codebase_rag.codebase_rag_types import ContextResult
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.sdk.select_relevant_chunks import select_relevant_chunks
from taskmates.workflows.codebase_rag.sdk.select_relevant_filenames import select_relevant_filenames


@transactional
async def gather_context(
        question: str,
        project_root: str = ".",
        file_pattern: str = "*.*"
) -> ContextResult:
    """
    Gather relevant code context for answering a question.

    This function orchestrates the two-phase selection process:
    1. Select relevant filenames from the project
    2. Select relevant code chunks from those files

    Args:
        question: The question to gather context for
        project_root: Root directory of the project
        file_pattern: File pattern to match (e.g., "*.py")

    Returns:
        ContextResult with selected code snippets and reasoning scratchpad
    """
    selected_filenames = await select_relevant_filenames(
        question=question,
        project_root=project_root,
        file_pattern=file_pattern
    )

    final_snippets, final_scratchpad = await select_relevant_chunks(
        question=question,
        selected_filenames=selected_filenames,
        project_root=project_root,
        file_pattern=file_pattern
    )

    return ContextResult(
        snippets=final_snippets,
        scratchpad=final_scratchpad
    )
