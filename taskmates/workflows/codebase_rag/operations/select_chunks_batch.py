from typing import List

from pydantic import ValidationError
from taskmates.lib.parse_output import parse_output
from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk, SelectionResult
from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.workflows.codebase_rag.operations.invoke_llm import invoke_llm
from taskmates.workflows.codebase_rag.operations.selection_schemas import create_chunk_selection_schema


async def select_chunks_batch(
        question: str,
        chunks: List[FileChunk],
        depth: int,
        batch_id: int,
        model_name: str = DEFAULT_MODEL_NAME
) -> SelectionResult:
    """
    Process a single batch of chunks for selection using structured output.

    CRITICAL: This function NEVER discards LLM selections. If the LLM returns URIs that don't
    match exactly, we use fuzzy matching to find the intended chunks. The LLM decides what's
    relevant - our job is to interpret its selections, not filter them out.

    Args:
        question: The user's question
        chunks: List of chunks to evaluate (max 50)
        depth: Current depth in navigation
        batch_id: Identifier for this batch
        model_name: Ollama model to use

    Returns:
        SelectionResult with selected URIs and reasoning
    """
    runtime.logger.info(f"Processing batch {batch_id} with {len(chunks)} chunks")

    system_message = """You are an expert code navigator. Your task is to:
1. Review ONLY the code chunks provided below
2. Identify which of THESE SPECIFIC chunks might contain information to answer the user's question
3. Record your reasoning for later reference

CRITICAL INSTRUCTIONS:
- Each chunk is labeled with a URI in the format: CHUNK (file:line_start-line_end)
- You MUST return the EXACT chunk URIs as shown in the parentheses
- Example: If you see "CHUNK (taskmates/types.py:1-132):", you must return "taskmates/types.py:1-132"
- Do NOT return just the file path (e.g., "taskmates/types.py")
- Do NOT suggest chunks that are not in the provided list
- If none of the provided chunks are relevant, return an empty array

You must respond with valid JSON matching this schema:
{
  "reasoning": "string - explanation of why these specific chunks are relevant (or why none are relevant)",
  "selected_chunks": ["array", "of", "EXACT", "chunk", "URIs", "including", "line", "numbers"]
}"""

    user_message = f"QUESTION: {question}\n\nCODE CHUNKS:\n\n"

    for chunk in chunks:
        # Show FULL chunk text - never truncate, let the LLM see everything
        user_message += f"CHUNK ({chunk['uri']}):\n{chunk['text']}\n\n"

    messages_data = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_message}
    ]

    response = await invoke_llm(messages_data=messages_data, model_name=model_name, format="json")
    response_text = response.get('content', '').strip() if response else ''

    if not response_text:
        runtime.logger.warning(f"LLM returned empty response for batch {batch_id}")
        return {
            'selected_uris': [],
            'scratchpad': ""
        }

    # Create schema with valid URIs baked in
    valid_uris = {chunk['uri'] for chunk in chunks}
    ChunkSelectionResult = create_chunk_selection_schema(valid_uris)

    try:
        # Parse JSON response using parse_output (has retry logic and validation)
        result = parse_output(
            response_text,
            ChunkSelectionResult
        )

        # Handle None or empty selected_chunks
        if result.selected_chunks is None:
            result.selected_chunks = []

        runtime.logger.info(f"Batch {batch_id} selected {len(result.selected_chunks)} chunks")

        return {
            'selected_uris': result.selected_chunks,
            'scratchpad': f"BATCH {batch_id} REASONING:\n{result.reasoning}"
        }

    except (ValidationError, Exception) as e:
        runtime.logger.error(f"Failed to parse chunk selection: {e}")
        runtime.logger.error(f"Response was: {response_text}")
        return {
            'selected_uris': [],
            'scratchpad': f"BATCH {batch_id} REASONING:\nError: {str(e)}"
        }
