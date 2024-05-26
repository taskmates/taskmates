import re
import textwrap

from taskmates.lib.str_.to_snake_case import to_snake_case

# from taskmates.frontends.markdown.generate_tool_call_id import generate_tool_call_id

TOOL_CALL_PATTERN = re.compile(
    r"^-\s(?P<function_name>.+?)\s\[(?P<tool_call_id>\d+)]\s`(?P<arguments>\{.*?})`$", re.MULTILINE)


def substitute_tool_calls(content) -> (list, str):
    return extract_tool_calls(content), extract_message_content(content)


def extract_tool_calls(content):
    tool_calls = []
    for match in re.finditer(TOOL_CALL_PATTERN, content):
        function_name = to_snake_case(match.group('function_name').strip())
        tool_call_id = match.group('tool_call_id')
        arguments = match.group('arguments')

        tool_call = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": function_name,
                "arguments": arguments
            }
        }
        tool_calls.append(tool_call)
    return tool_calls if tool_calls else None


def extract_message_content(content):
    # Split the content into lines
    lines = content.split("\n")

    # Find the index of the "Steps" header
    steps_index = next((i for i, line in enumerate(lines) if line.startswith("###### Steps")), -1)

    if steps_index == -1:
        # If "Steps" header is not found, return the original content
        return content

    # Extract the content before the "Steps" header
    message_content = "\n".join(lines[:steps_index])

    # If there is content before the "Steps" header, add a trailing newline
    # only if the content doesn't already end with a newline
    if message_content.strip() and not message_content.endswith("\n"):
        message_content += "\n"

    return message_content


# Updated test cases with the new syntax and expected behavior
def test_process_messages_with_single_tool_call():
    content = textwrap.dedent("""\
        Message content
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)
    tool_calls, message_content = substitute_tool_calls(content)

    assert tool_calls == [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"cmd":"cd /tmp"}'
            }
        }
    ]
    assert message_content == "Message content\n"


def test_process_messages_with_multiple_tool_calls():
    content = textwrap.dedent("""\
        Message content

        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        - Run Shell Command [2] `{"cmd":"ls"}`
    """)
    tool_calls, message_content = substitute_tool_calls(content)

    assert tool_calls == [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"cmd":"cd /tmp"}'
            }
        },
        {
            "id": "2",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"cmd":"ls"}'
            }
        }
    ]
    assert message_content == "Message content\n"


def test_process_messages_with_no_tool_calls():
    content = "Message content without tool calls\n"
    tool_calls, message_content = substitute_tool_calls(content)
    assert tool_calls is None
    assert message_content == "Message content without tool calls\n"


def test_process_messages_with_tool_calls_and_extra_content():
    content = textwrap.dedent("""\
        Message content
        Some extra content
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)
    tool_calls, message_content = substitute_tool_calls(content)

    assert tool_calls == [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"cmd":"cd /tmp"}'
            }
        }
    ]
    assert message_content == textwrap.dedent("""\
        Message content
        Some extra content
    """)


def test_process_messages_with_no_content_before_steps():
    content = textwrap.dedent("""\
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)
    tool_calls, message_content = substitute_tool_calls(content)

    assert tool_calls == [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"cmd":"cd /tmp"}'
            }
        }
    ]
    assert message_content == ""


def test_tool_call_pattern_single_line():
    tool_call_content = "- Run Shell Command [1] `{\"cmd\":\"cd /tmp\"}`\n"
    matches = re.finditer(TOOL_CALL_PATTERN, tool_call_content)
    tool_calls = [match.group() for match in matches]
    assert len(tool_calls) == 1
    assert tool_calls[0] == tool_call_content.strip()


def test_tool_call_pattern_multiple_lines():
    content = textwrap.dedent("""\
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        - Run Shell Command [2] `{"cmd":"ls"}`
    """)
    matches = re.finditer(TOOL_CALL_PATTERN, content)
    tool_calls = [match.group() for match in matches]
    assert len(tool_calls) == 2
    assert tool_calls[0] == "- Run Shell Command [1] `{\"cmd\":\"cd /tmp\"}`"
    assert tool_calls[1] == "- Run Shell Command [2] `{\"cmd\":\"ls\"}`"


def test_tool_call_pattern_with_additional_content():
    content = textwrap.dedent("""\
        Message content
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
    """)
    matches = re.finditer(TOOL_CALL_PATTERN, content)
    tool_calls = [match.group() for match in matches]
    assert len(tool_calls) == 1
    assert tool_calls[0] == "- Run Shell Command [1] `{\"cmd\":\"cd /tmp\"}`"


def test_tool_call_pattern_no_tool_calls():
    content = "Message content"
    matches = re.finditer(TOOL_CALL_PATTERN, content)
    tool_calls = [match.group() for match in matches if match]
    assert len(tool_calls) == 0
