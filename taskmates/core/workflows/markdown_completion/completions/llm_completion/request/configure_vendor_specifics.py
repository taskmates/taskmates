from typing import Tuple

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from typeguard import typechecked

from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import \
    FixtureChatModel


@typechecked
def configure_vendor_specifics(client: BaseChatModel, messages: list[dict], tools: list) -> Tuple[list, list]:
    """Configure messages and tools based on the vendor.

    Args:
        client: The LangChain chat model client
        messages: List of messages to potentially modify
        tools: List of tools to potentially modify

    Returns:
        Tuple of (messages, tools) with vendor-specific configurations applied
    """
    # Handle Anthropic-specific caching
    if isinstance(client, ChatAnthropic):
        _setup_anthropic_caching(messages)

    # Handle OpenAI-specific tools
    if "gpt-4" in (getattr(client, "model_name", "") or getattr(client, "model", "")):
        tools = tools.copy()  # Don't modify the original list
        webtool = {"type": "web_search_preview"}
        tools.append(webtool)

    # Handle xAI/Grok-specific Live Search
    if isinstance(client, ChatXAI):
        client.search_parameters = {
            "mode": "auto",
            # "max_search_results": 3,
        }

    return messages, tools


def _setup_anthropic_caching(messages: list[dict]) -> None:
    """Configure Anthropic-specific message caching.

    Args:
        messages: List of messages to add cache control to (modified in-place)
    """
    first_message = messages[0]
    if first_message["role"] == "system":
        first_message["content"] = [{
            "type": "text",
            "text": first_message["content"],
            "cache_control": {"type": "ephemeral"}
        }]

    # Add cache control to the last 3 non-system messages
    non_system_count = 0
    for message in reversed(messages):
        if not message["role"] == "system":
            if isinstance(message["content"], str):
                message["content"] = [{"type": "text", "text": message["content"]}]
            for content in message["content"]:
                if content["type"] == "text":
                    content["cache_control"] = {"type": "ephemeral"}
            non_system_count += 1
            if non_system_count >= 3:
                break


@pytest.mark.integration
def test_configure_vendor_specifics_with_openai():
    """Test that OpenAI GPT-4 models get web search tool added."""
    client = ChatOpenAI(model="gpt-4")
    messages = [{"role": "user", "content": "Hello"}]
    tools = [{"type": "function", "name": "existing_tool"}]

    result_messages, result_tools = configure_vendor_specifics(client, messages, tools)

    # Messages should be unchanged
    assert result_messages == messages

    # Tools should have web search added
    assert len(result_tools) == 2
    assert result_tools[0] == {"type": "function", "name": "existing_tool"}
    assert result_tools[1] == {"type": "web_search_preview"}


@pytest.mark.integration
def test_configure_vendor_specifics_with_anthropic():
    """Test that Anthropic models get caching configured."""
    from langchain_anthropic import ChatAnthropic
    from langchain.schema import SystemMessage, HumanMessage, AIMessage

    # Real Anthropic client
    client = ChatAnthropic(model="claude-3-haiku-20240307", api_key="dummy-key")

    # Real message objects
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="User message 1"),
        AIMessage(content="AI message 2"),
        HumanMessage(content="User message 3"),
        AIMessage(content="AI message 4"),
    ]

    tools = []

    result_messages, result_tools = configure_vendor_specifics(client, messages, tools)

    # Check system message has cache control
    assert messages[0].content == {
        "type": "text",
        "text": "System prompt",
        "cache_control": {"type": "ephemeral"}
    }

    # Check last 3 non-system messages have cache control
    expected_contents = [
        [{"type": "text", "text": "User message 1", "cache_control": {"type": "ephemeral"}}],
        [{"type": "text", "text": "AI message 2", "cache_control": {"type": "ephemeral"}}],
        [{"type": "text", "text": "User message 3", "cache_control": {"type": "ephemeral"}}],
    ]

    for i, expected in enumerate(expected_contents, 1):
        assert messages[i].content == expected

    # The 4th message should not have cache control
    assert messages[4].content == "AI message 4"

    # Tools should be unchanged
    assert result_tools == tools


def test_configure_vendor_specifics_with_xai():
    """Test that xAI/Grok models get Live Search parameters set."""
    client = ChatXAI(model="grok-4", api_key="dummy-key")
    messages = [{"role": "user", "content": "Hello"}]
    tools = [{"type": "function", "name": "existing_tool"}]

    # Verify search_parameters is not set initially
    assert not hasattr(client, "search_parameters") or client.search_parameters is None

    result_messages, result_tools = configure_vendor_specifics(client, messages, tools)

    # Messages and tools should be unchanged
    assert result_messages == messages
    assert result_tools == tools

    # Client should have search_parameters set
    assert client.search_parameters == {
        "mode": "auto",
    }


def test_configure_vendor_specifics_with_other_client():
    """Test that non-OpenAI/Anthropic/xAI clients pass through unchanged."""
    client = FixtureChatModel(fixture_path="dummy.jsonl")
    messages = [{"role": "user", "content": "Hello"}]
    tools = [{"type": "function", "name": "existing_tool"}]

    result_messages, result_tools = configure_vendor_specifics(client, messages, tools)

    # Everything should be unchanged
    assert result_messages == messages
    assert result_tools == tools
