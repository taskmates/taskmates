from typing import List

from taskmates.lib.parse_output import parse_output
from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk, AnswerResult, CodebaseAnswer
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.operations.invoke_llm import invoke_llm


@transactional
async def generate_answer(
        question: str,
        snippets: List[FileChunk],
        scratchpad: str,
        model_name: str = DEFAULT_MODEL_NAME
) -> AnswerResult:
    """
    Generate an answer from the retrieved code snippets.

    Args:
        question: The user's question
        snippets: Retrieved code snippets
        scratchpad: Navigation reasoning
        model_name: Ollama model to use

    Returns:
        AnswerResult with answer, citations, code snippets, and scratchpad
    """
    runtime.logger.info("\n==== GENERATING ANSWER ====")

    if not snippets:
        return {
            'answer': "I couldn't find relevant code to answer this question.",
            'citations': [],
            'code_snippets': [],
            'scratchpad': scratchpad
        }

    # Build context with token tracking - MUST match navigation's calculation exactly
    max_answer_tokens = 7000
    base_overhead = 1500  # System prompt, question, response format, scratchpad buffer
    available_for_snippets = max_answer_tokens - base_overhead

    system_prompt_base = """You are a code analysis assistant. Your task is to answer the user's question about a codebase.

You will be given:
1. CODE SNIPPETS - Raw code from the codebase
2. SCRATCHPAD - Analysis from the navigation process that explains what the code does
3. QUESTION - The user's question

Your answer should:
- Be based on the SCRATCHPAD's analysis (it already explains the code)
- Include citations to specific code snippets in the format path/to/file.py:start-end
- Be clear and directly answer the question

Format your response as:
- Answer: [Your explanation based on the scratchpad]
- Citations: [List of file:line citations that support your answer]"""

    valid_citations = []
    context = ""
    context_tokens = 0
    included_snippets = []

    # Add all snippets - they should all fit because navigation checked this
    for snippet in snippets:
        snippet_text = f"CODE SNIPPET {snippet['uri']}:\n{snippet['text']}\n\n"
        snippet_tokens = count_tokens(snippet_text)

        valid_citations.append(snippet['uri'])
        context += snippet_text
        context_tokens += snippet_tokens
        included_snippets.append(snippet)

    # Verify navigation did its job correctly
    if context_tokens > available_for_snippets:
        runtime.logger.error(f"BUG: Navigation returned {context_tokens} tokens but limit is {available_for_snippets}")
        runtime.logger.error(f"This should never happen - navigation should ensure all snippets fit")

    system_prompt = system_prompt_base + f"\n\nValid citations: {', '.join(valid_citations)}"

    messages_data = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f"CODE SNIPPETS:\n{context}\n\nSCRATCHPAD (Navigation reasoning):\n{scratchpad}\n\nQUESTION: {question}\n\nAnswer the question above using the scratchpad's analysis and citing the code snippets."}
    ]

    runtime.logger.info(f"Invoking LLM with {len(included_snippets)} snippets and scratchpad length {len(scratchpad)}")
    runtime.logger.debug(f"System prompt length: {len(system_prompt)}")
    runtime.logger.debug(f"Context length: {len(context)}")

    response = await invoke_llm(messages_data=messages_data, model_name=model_name)
    answer_text = response.get('content', '').strip() if response else ''

    if not answer_text:
        runtime.logger.error(f"LLM returned empty response")
        return {
            'answer': "Error: LLM returned empty response",
            'citations': [],
            'code_snippets': included_snippets,
            'scratchpad': scratchpad
        }

    runtime.logger.debug(f"LLM response: {answer_text[:500]}")
    runtime.logger.info(f"Full LLM response:\n{answer_text}")

    response: CodebaseAnswer = parse_output(answer_text, CodebaseAnswer)

    runtime.logger.info(f"Parsed response: answer={response.answer[:200]}, citations={response.citations}")

    for citation in response.citations:
        if "-" not in citation:
            runtime.logger.warning(f"Invalid citation format: {citation}")
        if ":" not in citation:
            runtime.logger.warning(f"Invalid citation format: {citation}")

    runtime.logger.info(f"\nAnswer: {response.answer}")
    runtime.logger.info(f"Citations: {response.citations}")

    return {
        'answer': response.answer,
        'citations': response.citations,
        'code_snippets': included_snippets,
        'scratchpad': scratchpad
    }
