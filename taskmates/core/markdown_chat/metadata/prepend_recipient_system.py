import datetime

import jinja2
from jinja2 import Environment
from typeguard import typechecked

from taskmates.core.markdown_chat.participants.compute_introduction_message import compute_introduction_message
from taskmates.core.markdown_chat.participants.format_username_prompt import format_username_prompt


@typechecked
def prepend_recipient_system(participants_configs: dict, recipient_config: dict, messages: list, inputs: dict | None) \
        -> list[dict]:
    if "name" not in recipient_config:
        return messages
    recipient = recipient_config["name"]
    if inputs is None:
        inputs = {}

    # Build context with message metadata
    context = {
        "inputs": inputs,
        "messages": messages
    }

    recipient_system_parts = []
    if recipient_config.get("system", None):
        # Render the recipient system message with context
        rendered_system = render_template(recipient_config.get("system"), context)
        recipient_system_parts.append(rendered_system.rstrip("\n") + "\n")
    introduction_message = compute_introduction_message(participants_configs)
    if introduction_message:
        recipient_system_parts.append(introduction_message)
    if recipient != "assistant":
        recipient_system_parts.append(format_username_prompt(recipient) + "\n")
    recipient_system = "\n".join(recipient_system_parts)

    # setup system
    if recipient_system != '':
        if messages[0]["role"] == "system":
            messages = [{"role": "system", "content": recipient_system}, *messages[1:]]
        else:
            messages = [{"role": "system", "content": recipient_system}, *messages]

    if messages[0]["role"] == "system":
        messages[0]["content"] = render_template(messages[0]["content"], context)

    return messages


def render_template(template, inputs):
    env = create_env()
    return env.from_string(template).render(inputs)


def create_env():
    env = Environment(
        autoescape=False,
        keep_trailing_newline=True,
        undefined=jinja2.Undefined)
    env.globals['datetime'] = datetime
    return env


def test_prepend_recipient_system_with_message_metadata(tmp_path):
    """Test that message metadata is available in template context."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "You are an assistant. {% if messages[-1].meta.type == 'question' %}Answer the question.{% else %}Process the request.{% endif %}"
        }
    }

    recipient_config = participants_configs["assistant"]

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "What is 2+2?",
            "meta": {"type": "question"}
        }
    ]

    result = prepend_recipient_system(participants_configs, recipient_config, messages, {})

    assert result[0]["role"] == "system"
    assert "Answer the question" in result[0]["content"]
    assert "Process the request" not in result[0]["content"]


def test_prepend_recipient_system_with_different_metadata(tmp_path):
    """Test that different metadata values produce different outputs."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "{% if messages[-1].meta.type == 'command' %}Execute the command.{% else %}Respond normally.{% endif %}"
        }
    }

    recipient_config = participants_configs["assistant"]

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Run ls",
            "meta": {"type": "command"}
        }
    ]

    result = prepend_recipient_system(participants_configs, recipient_config, messages, {})

    assert result[0]["role"] == "system"
    assert "Execute the command" in result[0]["content"]
    assert "Respond normally" not in result[0]["content"]


def test_prepend_recipient_system_with_last_message_object(tmp_path):
    """Test that last_message object is available in template."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": "User {{ messages[-1].name }} said: {{ messages[-1].content[:10] }}"
        }
    }

    recipient_config = participants_configs["assistant"]

    messages = [
        {
            "role": "user",
            "name": "john",
            "content": "Hello there, how are you?",
            "meta": {}
        }
    ]

    result = prepend_recipient_system(participants_configs, recipient_config, messages, {})

    assert result[0]["role"] == "system"
    assert "User john said: Hello ther" in result[0]["content"]


def test_prepend_recipient_system_with_complex_conditionals(tmp_path):
    """Test complex conditional logic based on metadata."""
    participants_configs = {
        "assistant": {
            "name": "assistant",
            "role": "assistant",
            "system": """{% if messages[-1].meta.priority == 'high' %}
URGENT: Handle this immediately.
{% elif messages[-1].meta.priority == 'medium' %}
Handle this soon.
{% else %}
Handle this when convenient.
{% endif %}"""
        }
    }

    recipient_config = participants_configs["assistant"]

    messages = [
        {
            "role": "user",
            "name": "user",
            "content": "Fix the bug",
            "meta": {"priority": "high"}
        }
    ]

    result = prepend_recipient_system(participants_configs, recipient_config, messages, {})

    assert result[0]["role"] == "system"
    assert "URGENT: Handle this immediately" in result[0]["content"]
    assert "Handle this soon" not in result[0]["content"]
