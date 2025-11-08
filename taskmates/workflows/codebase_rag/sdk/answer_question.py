from loguru import logger

from taskmates.workflows.codebase_rag.codebase_rag_types import AnswerResult
from taskmates.workflows.codebase_rag.operations.generate_answer import generate_answer
from taskmates.workflows.codebase_rag.sdk.gather_context import gather_context


async def answer_question(
        question: str,
        project_root: str,
        file_pattern: str
) -> AnswerResult:
    """
    Complete RAG process: gather context and generate answer.
    
    This is the main entry point for the codebase RAG workflow. It:
    1. Gathers relevant code context (files and chunks)
    2. Generates an answer based on the context
    
    Args:
        question: The question to answer about the codebase
        project_root: Root directory of the project
        file_pattern: File pattern to match (e.g., "*.py")
        
    Returns:
        AnswerResult with answer, citations, and code snippets
    """
    logger.info(f"Starting RAG process for question: {question[:100]}...")

    context = await gather_context(
        question=question,
        project_root=project_root,
        file_pattern=file_pattern
    )

    answer_result = await generate_answer(
        question=question,
        snippets=context['snippets'],
        scratchpad=context['scratchpad']
    )

    logger.info(f"Answer generated")
    logger.info(f"Answer preview: {answer_result['answer'][:200]}...")
    logger.info(f"Citations: {answer_result['citations']}")
    logger.info(f"Code snippets used: {len(answer_result['code_snippets'])}")

    return answer_result
