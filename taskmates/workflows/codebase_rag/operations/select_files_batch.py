from typing import List

from pydantic import ValidationError
from taskmates.lib.parse_output import parse_output
from taskmates.workflows.codebase_rag.codebase_rag_types import SelectionResult, SelectableItem
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.workflows.codebase_rag.operations.invoke_llm import invoke_llm
from taskmates.workflows.codebase_rag.operations.selection_schemas import create_file_selection_schema


async def select_files_batch(
        question: str,
        batch: List[SelectableItem],
        batch_id: int,
        total_batches: int,
        model_name: str
) -> SelectionResult:
    """
    Select relevant files from a single batch using structured output.

    CRITICAL: This function NEVER discards LLM selections. If the LLM returns URIs that don't
    match exactly, we use fuzzy matching to find the intended files. The LLM decides what's
    relevant - our job is to interpret its selections, not filter them out.

    Args:
        question: The user's question
        batch: Batch of file items to evaluate
        batch_id: Index of this batch
        total_batches: Total number of batches
        model_name: Ollama model to use

    Returns:
        SelectionResult with selected file URIs and reasoning
    """
    runtime.logger.info(f"Processing file batch {batch_id + 1}/{total_batches} with {len(batch)} files")

    system_message = """You are an expert code navigator. Your task is to identify which files might contain information to answer the user's question based solely on their file paths and names.

CRITICAL: You MUST select ONLY from the file paths provided in the input below. Do NOT suggest other files.
If none of the provided files are relevant, return an empty array for selected_files.

Consider:
- File names that suggest relevant functionality
- Directory structure that indicates related code
- Common naming conventions in the codebase

Be selective but thorough - choose files that are most likely relevant.

You must respond with valid JSON matching this schema:
{
  "reasoning": "string - explanation of why these specific files are relevant (or why none are relevant)",
  "selected_files": ["array", "of", "file", "paths", "from", "the", "provided", "list", "ONLY"]
}"""

    user_message = f"QUESTION: {question}\n\nFILE PATHS (batch {batch_id + 1}/{total_batches}):\n\n"
    for item in batch:
        user_message += f"- {item['uri']}\n"

    messages_data = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': user_message}
    ]

    response = await invoke_llm(messages_data=messages_data, model_name=model_name, format="json")
    response_text = response.get('content', '').strip() if response else ''

    if not response_text:
        runtime.logger.warning(f"LLM returned empty response for file selection batch {batch_id + 1}")
        return {'selected_uris': [], 'scratchpad': ""}

    # Create schema with valid URIs baked in
    valid_uris = {item['uri'] for item in batch}
    FileSelectionResult = create_file_selection_schema(valid_uris)

    try:
        # Parse JSON response using parse_output (has retry logic and validation)
        runtime.logger.debug(f"Parsing JSON response of length {len(response_text)}")
        result = parse_output(
            response_text,
            FileSelectionResult
        )
        runtime.logger.debug(
            f"Parsed successfully, got {len(result.selected_files) if result.selected_files else 0} files")

        # Handle None or empty selected_files
        if result.selected_files is None:
            runtime.logger.warning("selected_files is None, setting to empty list")
            result.selected_files = []

        runtime.logger.info(
            f"Batch {batch_id + 1}/{total_batches}: selected {len(result.selected_files)} files")

        return {
            'selected_uris': result.selected_files,
            'scratchpad': result.reasoning
        }

    except (ValidationError, Exception) as e:
        runtime.logger.error(f"Failed to parse file selection: {e}")
        runtime.logger.error(f"Response was: {response_text}")
        return {'selected_uris': [], 'scratchpad': str(e)}
