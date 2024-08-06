import json
from typing import List, Dict, Any

from taskmates.core.chat_completion.openai_adapters.anthropic_openai_adapter.parsing.get_image_contents import \
    get_image_contents
from taskmates.core.chat_completion.openai_adapters.anthropic_openai_adapter.parsing.get_tool_contents import \
    get_tool_contents
from taskmates.lib.openai_.model.chat_completion_chunk_model import ChatCompletionChunkModel
from typeguard import typechecked

from taskmates.formats.openai.get_text_content import get_text_content


def join_text_contents(contents: list) -> str:
    return "".join(content for content in contents if content)


def get_tool_use_contents(message):
    # example tool call
    # [{'function': {'arguments': '{"cmd": "pwd"}', 'name': 'run_shell_command'}, 'id': '1', 'type': 'function'}]

    # example tool use
    # {
    #     "type": "tool_use",
    #     "id": "toolu_01A09q90qw90lq917835lq9",
    #     "name": "get_weather",
    #     "input": {"location": "San Francisco, CA", "unit": "celsius"}
    # }

    tool_uses = []
    tool_calls = message.get("tool_calls", [])
    for tool_call in tool_calls:
        tool_use = {
            "type": "tool_use",
            "id": tool_call['id'],
            "name": tool_call["function"]["name"],
            "input": json.loads(tool_call["function"]["arguments"])
        }
        tool_uses.append(tool_use)

    return tool_uses


@typechecked
def convert_and_merge_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    processed_messages = []
    previous_role = None

    previous_text_contents = []
    previous_image_contents = []
    previous_tool_use_contents = []
    previous_tool_contents = []

    for message in messages:
        if isinstance(message, dict):
            message_role = message['role']
            message_text_content = get_text_content(message)
            message_image_contents = get_image_contents(message)
            message_tool_use_contents = get_tool_use_contents(message)
            message_tool_contents = get_tool_contents(message)
        elif isinstance(message, ChatCompletionChunkModel):
            message_role = message.choices[0].delta.role
            message_text_content = message.choices[0].delta.content
            message_image_contents = []
            message_tool_use_contents = message.choices[0].delta.tool_calls or []
            message_tool_contents = []
        else:
            raise ValueError(f"Unexpected message type: {type(message)}")

        # Convert name to prefix
        if 'name' in message and message_role != 'tool':
            name = message.pop("name")
            if not message_text_content.startswith(f"**{name}>** "):
                message_text_content = f"**{name}>** {message_text_content}"

        if message_text_content:
            message_text_contents = [message_text_content]

        # If the message is a tool, we want to treat it as a user message
        if message_role == 'tool':
            message_role = 'user'
            message_text_contents = []

        is_same_role = message_role == previous_role
        is_first_message = previous_role is None

        if is_same_role or is_first_message:
            # just collect the messages
            previous_role = message_role
            previous_text_contents.extend(message_text_contents)
            previous_image_contents.extend(message_image_contents)
            previous_tool_use_contents.extend(message_tool_use_contents)
            previous_tool_contents.extend(message_tool_contents)
        else:
            # roles changed

            # time to process the buffered content
            previous_message_content = build_content(previous_tool_use_contents,
                                                     previous_tool_contents,
                                                     previous_text_contents,
                                                     previous_image_contents)
            processed_messages.append({"role": previous_role, "content": previous_message_content})

            # reset the buffers
            previous_role = message_role
            previous_text_contents = message_text_contents
            previous_image_contents = message_image_contents
            previous_tool_use_contents = message_tool_use_contents
            previous_tool_contents = message_tool_contents

    # Process the last message
    if previous_text_contents or previous_image_contents or previous_tool_contents or previous_tool_use_contents:
        processed_messages.append(
            {"role": previous_role,
             "content": build_content(previous_tool_use_contents,
                                      previous_tool_contents,
                                      previous_text_contents,
                                      previous_image_contents)})
    return processed_messages


def build_content(previous_tool_use_contents, previous_tool_contents, previous_text_contents,
                  previous_image_contents):
    previous_tool_use_contents = previous_tool_use_contents or []
    previous_tool_contents = previous_tool_contents or []
    previous_text_contents = previous_text_contents or []
    previous_image_contents = previous_image_contents or []
    text_only = previous_text_contents and not previous_image_contents and not previous_tool_contents and not previous_tool_use_contents
    if text_only:
        updated_content = join_text_contents(previous_text_contents)
    else:
        updated_content = []
        updated_content.extend(previous_tool_use_contents)
        updated_content.extend(previous_tool_contents)
        if previous_text_contents:
            updated_content.append({"type": "text", "text": join_text_contents(previous_text_contents)})
        updated_content.extend(previous_image_contents)
    return updated_content


def test_handling_messages_with_names():
    messages = [{"role": "user", "name": "Alice", "content": "Hello"}]
    expected = [{"role": "user", "content": "**Alice>** Hello"}]
    assert convert_and_merge_messages(messages) == expected


def test_handling_messages_with_names_in_content():
    messages = [{"role": "user", "name": "Alice", "content": "**Alice>** Hello"}]
    expected = [{"role": "user", "content": "**Alice>** Hello"}]
    assert convert_and_merge_messages(messages) == expected


def test_joining_messages_with_same_role():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "How are you?"}
    ]
    expected = [{"role": "user", "content": "Hello\nHow are you?"}]


def test_joining_messages_with_images():
    base64_image = "dGVzdA=="  # base64 encoded "test"
    messages = [
        {"role": "user", "content": "Message before\n"},
        {"role": "user",
         "content": [
             {"type": "text", "text": "Message with image:\n"},
             {
                 "image_url": {
                     "url": f"data:image/jpeg;base64,{base64_image}"
                 }
             }
         ]
         },
        {"role": "user", "content": "Message after\n"},

    ]
    expected = [
        {"role": "user", "content": [
            {"type": "text", "text": "Message before\nMessage with image:\nMessage after\n"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}}]}
    ]
    assert convert_and_merge_messages(messages) == expected


def test_joining_messages_with_tools():
    assistant_text_content = "Tool call text content\n"
    function_response = "my function response"
    user_text_content = "User text content\n"
    tool_use_id = "1234"
    function_name = "my_func"

    messages = [
        {"role": "assistant", "content": assistant_text_content},
        {"role": "tool", "name": function_name, "tool_call_id": tool_use_id, "content": function_response},
        {"role": "user", "content": user_text_content},

    ]
    expected = [
        {"role": "assistant", "content": assistant_text_content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": function_response
                },
                {"type": "text", "text": user_text_content},
            ]
        }
    ]
    assert convert_and_merge_messages(messages) == expected
