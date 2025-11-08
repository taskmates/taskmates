import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, ToolCall
from langchain_core.tools import BaseTool
from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.prepend_recipient_system import prepend_recipient_system
from taskmates.core.tools_registry import tools_registry
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request._convert_function_to_langchain_tool import \
    _convert_function_to_langchain_tool
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.configure_vendor_specifics import \
    configure_vendor_specifics


@typechecked
def build_llm_args(
        messages: list[dict],
        available_tools: list[str],
        participants: dict,
        inputs: dict,
        model_conf: dict,
        client=None
) -> dict:
    """
    Prepare the request payload for LLM completion.

    Returns:
        Dict with keys:
        - messages: List of LangChain BaseMessage objects
        - tools: List of LangChain BaseTool objects
        - model_params: Dict of model configuration parameters (temperature, max_tokens, etc.)
    """
    tools = list(map(tools_registry.__getitem__, available_tools))

    # TODO: we can probably move this to `prepend_recipient_system`
    # Get participants and recipient config
    participants_configs = participants

    # TODO: we can probably move this to `prepend_recipient_system`
    # Find recipient config - look for the participant that matches the last message's recipient
    recipient_config = {}
    if messages:
        last_message = messages[-1]
        recipient_name = last_message.get("recipient")
        if recipient_name and recipient_name in participants_configs:
            recipient_config = participants_configs[recipient_name]

    messages = messages

    if recipient_config.get('role') == 'assistant':
        # Prepend recipient system message if needed
        messages = prepend_recipient_system(
            participants_configs,
            recipient_config,
            messages,
            inputs
        )

    # filter out metadata
    # TODO: whitelist valid values instead of blacklist
    messages = [{key: value for key, value in m.items()
                 if key not in ("recipient", "recipient_role", "code_cells", "meta")}
                for m in messages]

    # convert "arguments" to str
    for message in messages:
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            tool_call["function"]["arguments"] = json.dumps(tool_call["function"]["arguments"],
                                                            ensure_ascii=False)

    # Apply vendor-specific configurations if client is provided
    if client is not None:
        messages, tools = configure_vendor_specifics(client, messages, tools)

    # Convert messages to LangChain format
    role_map = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
        "tool": ToolMessage,
    }

    langchain_messages = []
    for msg in messages:
        content = msg["content"] or ""

        raw_tool_calls = msg.get("tool_calls", [])
        tool_calls = []

        for tool_call in raw_tool_calls:
            id = tool_call["id"]
            type = tool_call["type"]
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            tool_calls.append(ToolCall(name=name, args=args, id=id, type=type))

        msg_args = dict(
            content=content,
            tool_calls=tool_calls
        )

        if "tool_call_id" in msg:
            msg_args["tool_call_id"] = msg.get("tool_call_id")

        message = role_map[msg["role"]](**msg_args)
        langchain_messages.append(message)

    # Convert tools to LangChain format
    langchain_tools: list[BaseTool] = []
    for tool in tools:
        if callable(tool):
            langchain_tool = _convert_function_to_langchain_tool(tool)
            langchain_tools.append(langchain_tool)
        else:
            langchain_tools.append(tool)

    # Prepare model parameters (excluding messages and tools)
    model_params = model_conf.get("client", {}).get("kwargs", {})

    return {
        "messages": langchain_messages,
        "tools": langchain_tools,
        "model_params": model_params
    }


def test_prepare_request_payload_basic_structure():
    """Test that prepare_request_payload returns the correct basic structure."""
    messages = [
        {"role": "user", "content": "Hello", "recipient": "assistant", "recipient_role": "assistant"}
    ]
    available_tools = []
    participants = {}
    inputs = {}
    model_conf = {
        "client": {"kwargs": {"model": "gpt-4o-mini", "temperature": 0.7}}
    }

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert "messages" in result
    assert "tools" in result
    assert "model_params" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "Hello"
    assert len(result["tools"]) == 0
    assert result["model_params"]["model"] == "gpt-4o-mini"
    assert result["model_params"]["temperature"] == 0.7


def test_prepare_request_payload_filters_metadata_from_messages():
    """Test that metadata fields are filtered from messages."""
    messages = [
        {
            "role": "user",
            "content": "Hello",
            "recipient": "assistant",
            "recipient_role": "assistant",
            "code_cells": ["some code"]
        }
    ]
    available_tools = []
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "Hello"


def test_prepare_request_payload_converts_tool_call_arguments_to_json():
    """Test that tool call arguments are converted to JSON strings and then parsed."""
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": {"location": "San Francisco", "unit": "celsius"}
                    }
                }
            ]
        }
    ]
    available_tools = ["get_weather"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert len(result["messages"][0].tool_calls) == 1
    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["name"] == "get_weather"
    assert tool_call["args"] == {"location": "San Francisco", "unit": "celsius"}


def test_prepare_request_payload_includes_tools_when_available():
    """Test that tools are included when available_tools is not empty."""
    messages = [
        {"role": "user", "content": "What's the weather?"}
    ]
    available_tools = ["get_weather"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["tools"]) == 1
    assert isinstance(result["tools"][0], BaseTool)
    assert result["tools"][0].name == "get_weather"


def test_prepare_request_payload_excludes_tools_when_not_available():
    """Test that tools list is empty when available_tools is empty."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    available_tools = []
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["tools"]) == 0


def test_prepare_request_payload_with_vendor_specifics():
    """Test that vendor-specific configurations are applied when client is provided."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    available_tools = ["echo"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import \
        FixtureChatModel

    client = FixtureChatModel(fixture_path="dummy.jsonl")

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=client)

    assert len(result["messages"]) == 1
    assert len(result["tools"]) == 1


def test_prepare_request_payload_preserves_model_conf_parameters():
    """Test that all model_conf parameters are preserved in model_params."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    available_tools = []
    participants = {}
    inputs = {}
    model_conf = {
        "client": {
            "kwargs": {
                "model": "gpt-4o-mini",
                "temperature": 0.8,
                "max_tokens": 100,
                "top_p": 0.9,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.3
            }
        }
    }

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert result["model_params"]["model"] == "gpt-4o-mini"
    assert result["model_params"]["temperature"] == 0.8
    assert result["model_params"]["max_tokens"] == 100
    assert result["model_params"]["top_p"] == 0.9
    assert result["model_params"]["frequency_penalty"] == 0.5
    assert result["model_params"]["presence_penalty"] == 0.3


def test_prepare_request_payload_handles_multiple_messages():
    """Test that multiple messages are correctly processed."""
    messages = [
        {"role": "user", "content": "Hello", "recipient": "assistant"},
        {"role": "assistant", "content": "Hi there!", "recipient_role": "assistant"},
        {"role": "user", "content": "How are you?", "recipient": "assistant"}
    ]
    available_tools = []
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["messages"]) == 3
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "Hello"
    assert isinstance(result["messages"][1], AIMessage)
    assert result["messages"][1].content == "Hi there!"
    assert isinstance(result["messages"][2], HumanMessage)
    assert result["messages"][2].content == "How are you?"


def test_prepare_request_payload_handles_tool_response_messages():
    """Test that tool response messages are correctly processed."""
    messages = [
        {"role": "user", "content": "What's the weather?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": {"location": "SF"}
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "name": "get_weather",
            "content": "Sunny, 72°F"
        }
    ]
    available_tools = ["get_weather"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["messages"]) == 3
    assert isinstance(result["messages"][2], ToolMessage)
    assert result["messages"][2].content == "Sunny, 72°F"
    assert result["messages"][2].tool_call_id == "call_123"


def test_prepare_request_payload_handles_unicode_in_tool_arguments():
    """Test that Unicode characters in tool arguments are preserved."""
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "arguments": {"message": "Hello 世界 🌍"}
                    }
                }
            ]
        }
    ]
    available_tools = ["echo"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["args"]["message"] == "Hello 世界 🌍"


def test_prepare_request_payload_returns_langchain_types():
    """Test that the return values are LangChain types."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    available_tools = ["echo"]
    participants = {}
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    assert isinstance(result, dict)
    assert "messages" in result
    assert "tools" in result
    assert "model_params" in result
    assert isinstance(result["messages"], list)
    assert all(isinstance(msg, BaseMessage) for msg in result["messages"])
    assert isinstance(result["tools"], list)
    assert all(isinstance(tool, BaseTool) for tool in result["tools"])
    assert isinstance(result["model_params"], dict)


def test_build_llm_args_with_metadata_in_template(tmp_path):
    """Test that message metadata is available in recipient system template."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": """You are a helpful assistant.

{% if messages[-1].meta.type == 'question' %}
When answering questions, be concise and accurate.
{% elif messages[-1].meta.type == 'command' %}
When executing commands, be careful and explain what you're doing.
{% else %}
Respond appropriately to the user's message.
{% endif %}"""
        }
    }

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "What is 2+2?",
            "recipient": "assistant",
            "meta": {"type": "question"}
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    # Find the system message
    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert "When answering questions, be concise and accurate" in system_message.content
    assert "When executing commands" not in system_message.content


def test_build_llm_args_with_different_metadata(tmp_path):
    """Test that different metadata values produce different system messages."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": """{% if messages[-1].meta.priority == 'high' %}
URGENT: Handle this immediately.
{% else %}
Handle this normally.
{% endif %}"""
        }
    }

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Fix the critical bug!",
            "recipient": "assistant",
            "meta": {"priority": "high"}
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert "URGENT: Handle this immediately" in system_message.content
    assert "Handle this normally" not in system_message.content


def test_build_llm_args_with_messages_object(tmp_path):
    """Test that last_message object is available in template."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "Responding to {{ messages[-1].name }}."
        }
    }

    messages = [
        {
            "role": "user",
            "name": "john",
            "content": "Hello!",
            "recipient": "assistant"
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert "Responding to john" in system_message.content


def test_build_llm_args_with_multiple_metadata_fields(tmp_path):
    """Test that multiple metadata fields are all available."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": """Type: {{ messages[-1].meta.type }}
Category: {{ messages[-1].meta.category }}
Priority: {{ messages[-1].meta.priority }}"""
        }
    }

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Help me with this task.",
            "recipient": "assistant",
            "meta": {
                "type": "request",
                "category": "support",
                "priority": "medium"
            }
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert "Type: request" in system_message.content
    assert "Category: support" in system_message.content
    assert "Priority: medium" in system_message.content


def test_build_llm_args_without_metadata(tmp_path):
    """Test that templates work when no metadata is present."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "{% if messages[-1].meta.type %}Type: {{ messages[-1].meta.type }}{% else %}No type specified{% endif %}"
        }
    }

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Hello!",
            "recipient": "assistant",
            "meta": {}
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {}
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert "No type specified" in system_message.content


def test_build_llm_args_with_inputs_from_run_opts(tmp_path):
    """Test that inputs from run_opts are available in templates."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "User's name is {{ inputs.user_name }}. Their role is {{ inputs.user_role }}."
        }
    }

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Hello!",
            "recipient": "assistant"
        }
    ]
    available_tools = []
    participants = participants_configs
    inputs = {
        "user_name": "Alice",
        "user_role": "developer"
    }
    model_conf = {"model": "gpt-4o-mini"}

    result = build_llm_args(messages, available_tools, participants, inputs, model_conf, client=None)

    system_message = next((msg for msg in result["messages"] if isinstance(msg, SystemMessage)), None)
    assert system_message is not None
    assert system_message.content == "User's name is Alice. Their role is developer.\n"
