from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.operations.invoke_llm import invoke_llm


@transactional
async def summarize_scratchpad(
        scratchpad: str,
        question: str,
        model_name: str = DEFAULT_MODEL_NAME
) -> str:
    """
    Summarize and deduplicate scratchpad content using LLM.

    Args:
        scratchpad: The accumulated scratchpad content
        question: The user's question for context
        model_name: Ollama model to use

    Returns:
        Summarized scratchpad without duplication
    """
    runtime.logger.info(f"Summarizing scratchpad ({len(scratchpad)} chars)")

    system_prompt = """You are an expert at summarizing technical reasoning.

Your task is to:
1. Remove duplicate information and redundant explanations
2. Consolidate similar reasoning from different batches
3. Keep all unique insights and important details
4. Maintain the logical flow of the navigation process
5. Keep it concise but comprehensive

Focus on what code was selected and why, removing verbose explanations."""

    messages_data = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f"QUESTION: {question}\n\nSummarize this navigation reasoning, removing duplicates and noise:\n\n{scratchpad}"}
    ]

    response = await invoke_llm(messages_data=messages_data, model_name=model_name)
    summarized = response.get('content', '').strip() if response else ''

    runtime.logger.info(f"Scratchpad summarized from {len(scratchpad)} to {len(summarized)} chars")

    return summarized


async def test_summarize_scratchpad():
    """Test scratchpad summarization."""
    scratchpad = """BATCH 0 REASONING:
Looking at chunks 0-49, I found relevant code in chunk 5 and chunk 12.

BATCH 1 REASONING:
Looking at chunks 50-99, I found relevant code in chunk 67 and chunk 78.

BATCH 2 REASONING:
Looking at chunks 100-120, I found relevant code in chunk 105."""

    question = "How does the parser work?"

    result = await summarize_scratchpad(
        scratchpad=scratchpad,
        question=question,
        model_name=DEFAULT_MODEL_NAME
    )

    assert isinstance(result, str)
    assert len(result) > 0
