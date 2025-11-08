from typing import List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from taskmates.core.workflow_engine.transactions.transactional import transactional


@transactional
async def invoke_llm(
    messages_data: List[Dict[str, Any]],
    model_name: str,
    format: str = None
) -> Dict[str, Any]:
    """
    Invoke an LLM with the given messages.

    This is a transactional wrapper that caches LLM responses.

    Args:
        messages_data: List of message dicts with 'role' and 'content' keys
                      Example: [{'role': 'system', 'content': '...'}, {'role': 'user', 'content': '...'}]
        model_name: Name of the Ollama model to use
        format: Optional format constraint (e.g., "json")

    Returns:
        The full LLM response as a dict (from response.model_dump())
    """
    # Convert message dicts to LangChain message objects
    messages = []
    for msg in messages_data:
        if msg['role'] == 'system':
            messages.append(SystemMessage(content=msg['content']))
        elif msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        else:
            raise ValueError(f"Unknown message role: {msg['role']}")

    if format:
        llm = ChatOllama(model=model_name, format=format)
    else:
        llm = ChatOllama(model=model_name)

    response = await llm.ainvoke(messages)
    return response.model_dump()
