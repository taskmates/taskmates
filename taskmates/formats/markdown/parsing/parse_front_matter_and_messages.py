import textwrap
import time
from pathlib import Path
from typing import Tuple, List, Dict, Union

import pyparsing
from loguru import logger
from typeguard import typechecked

from taskmates.grammar.parsers.markdown_chat_parser import markdown_chat_parser
from taskmates.lib.logging_.file_logger import file_logger


@typechecked
def parse_front_matter_and_messages(source_file: Path,
                                    content: str,
                                    implicit_role: str) -> Tuple[
    List[Dict[str, Union[str, list[dict]]]], Dict[str, any]]:
    transclusions_base_dir = source_file.parent

    messages: list[dict] = []

    start_time = time.time()  # Record the start time
    logger.debug(f"[parse_front_matter_and_messages] Parsing markdown: {start_time}-chat.md")

    parser = markdown_chat_parser()

    end_time = time.time()  # Record the end time
    time_taken = end_time - start_time
    logger.debug(f"[parse_front_matter_and_messages] Parsed markdown {start_time}-chat.md in {time_taken:.4f} seconds")

    file_logger.debug(f"[parse_front_matter_and_messages] {start_time}-chat.md", content=content)

    try:
        parsed_chat = parser.parse_string(content)
    except pyparsing.exceptions.ParseSyntaxException as e:
        # import pyparsing as pp
        # ppt = pp.testing
        # print(ppt.with_line_numbers(content))

        logger.error(f"Failed to parse markdown: /var/tmp/taskmates/logs/{start_time}-chat.md")
        logger.error(e)
        raise
    front_matter = parsed_chat.front_matter or {}

    # If the front_matter contains a `system` key, prepend it as the system message
    if 'system' in front_matter:
        messages = [{"role": "system", "content": front_matter['system']}] + messages

    for parsed_message in parsed_chat.messages:
        message_dict = parsed_message.as_dict()
        name = message_dict["name"]
        attributes = message_dict.get("attributes", {})

        message = {**({"role": message_dict["role"]} if "role" in message_dict else {}),
                   "name": name,
                   "content": message_dict["content"],
                   **({"code_cell_id": message_dict["code_cell_id"]} if "code_cell_id" in message_dict else {}),
                   **({"tool_call_id": message_dict["tool_call_id"]} if "tool_call_id" in message_dict else {}),
                   **({"tool_calls": message_dict["tool_calls"]} if "tool_calls" in message_dict else {}),
                   **attributes}

        messages.append(message)

        # TODO: process cell outputs here

    # set assistant roles
    for message in messages:
        if "role" in message:
            continue
        if message.get("name") in ("assistant", "user", "system", "tool"):
            message["role"] = message.get("name")
        else:
            message["role"] = "user"

    # set proper tool_call_ids
    global_tool_call_id = 1
    for message in messages:
        if message.get("tool_call_id"):
            message["tool_call_id"] = str(global_tool_call_id)
            global_tool_call_id += 1

    for message in messages:
        if message.get("role") == "cell_output":
            output_name = message["name"]
            message["name"] = "cell_output"
            message["role"] = "user"
            message["content"] = f"###### Cell Output: {output_name} [{message['code_cell_id']}]\n" + message[
                "content"]

    # remove duplicate/incomplete messages
    messages = deduplicate_messages(messages)

    return messages, front_matter


def deduplicate_messages(messages: List[Dict[str, Union[str, list[dict]]]]) -> List[Dict[str, Union[str, list[dict]]]]:
    deduplicated_messages = []
    i = 0
    while i < len(messages):
        current_message = messages[i]
        if current_message['role'] == 'assistant':
            # Check if the next message is a duplicate
            if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant' and messages[i + 1].get(
                    'name') == current_message.get('name'):
                i += 1
                continue
        deduplicated_messages.append(current_message)
        i += 1
    return deduplicated_messages


def test_parse_chat_messages_with_internal_header(tmp_path):
    input = """\
        **user>** Here is a message.
         
        **This one is not** a message
        
        **assistant>** Here is another message.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n**This one is not** a message\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is another message.\n'}
    ]
    assert messages == expected_messages


def test_parse_chat_messages_with_frontmatter(tmp_path):
    input = """\
        ---
        key1: value1
        key2: 
          - item1
          - item2
        ---
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    expected_front_matter = {'key1': 'value1', 'key2': ['item1', 'item2']}
    assert messages == expected_messages and front_matter == expected_front_matter


def test_parse_chat_messages_with_metadata(tmp_path):
    input = """\
        **user {"name": "john", "age": 30}>** Here is a message from John.
        
        **assistant {"model": "gpt-3.5-turbo"}>** Here is a response from the assistant.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Here is a message from John.\n\n'
    assert messages[0]['name'] == 'john'
    assert messages[0]['age'] == 30
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['content'] == 'Here is a response from the assistant.\n'
    assert messages[1]['model'] == 'gpt-3.5-turbo'


def test_parse_chat_messages_with_system_in_frontmatter(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 3
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == 'Here is a message.\n\n'
    assert messages[2]['role'] == 'assistant'
    assert messages[2]['content'] == 'Here is a response.\n'


def test_parse_chat_messages_with_system_in_frontmatter_and_content(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **system>** This is a system message from the content.
        
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 4
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'system'
    assert messages[1]['content'] == 'This is a system message from the content.\n\n'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'Here is a message.\n\n'
    assert messages[3]['role'] == 'assistant'
    assert messages[3]['content'] == 'Here is a response.\n'


def test_parse_chat_messages_with_tool_calls_and_execution(tmp_path):
    input = """\
        **assistant>** Here is a message.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        
        **user>** Here is another message.

        """

    expected_messages = [
        {
            'role': 'assistant',
            'name': 'assistant',
            'content': 'Here is a message.\n\n',
            'tool_calls': [
                {
                    'id': '1',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': {"cmd": "cd /tmp"}
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n\n'
        },
        {
            'role': 'user',
            'name': 'user',
            'content': 'Here is another message.\n\n'
        }
    ]

    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")

    assert messages == expected_messages


def test_parse_chat_messages_with_multiple_tool_calls_and_missing_execution(tmp_path):
    input = textwrap.dedent("""\
        USER INSTRUCTION

        **shell>**

        ###### Steps

        - Run Shell Command [1] `{"cmd": "cd /tmp && ls"}`
        - Run Shell Command [2] `{"cmd": "date"}`

        ###### Execution: Run Shell Command [1]

        <pre>
        OUTPUT 1
        </pre>

        ###### Execution: Run Shell Command [2]

        <pre>
        OUTPUT 2
        </pre>
        """)
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

    expected_messages = [
        {
            'role': 'user',
            'name': 'user',
            'content': 'USER INSTRUCTION\n\n'
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '\n',
            'tool_calls': [
                {
                    'id': '1',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': {'cmd': 'cd /tmp && ls'}
                    }
                },
                {
                    'id': '2',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': {'cmd': 'date'}
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n'
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '2',
            'content': '\n<pre>\nOUTPUT 2\n</pre>\n'
        }
    ]

    assert messages == expected_messages


def test_parse_chat_messages_with_multiple_tool_calls_in_separate_messages(tmp_path):
    input = textwrap.dedent("""\
        USER INSTRUCTION

        **shell>**

        ###### Steps

        - Run Shell Command [1] `{"cmd": "cd /tmp && ls"}`

        ###### Execution: Run Shell Command [1]

        <pre>
        OUTPUT 1
        </pre>

        **shell>**

        ###### Steps

        - Run Shell Command [2] `{"cmd": "date"}`

        ###### Execution: Run Shell Command [2]

        <pre>
        OUTPUT 2
        </pre>
        """)
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

    expected_messages = [
        {
            'role': 'user',
            'name': 'user',
            'content': 'USER INSTRUCTION\n\n'
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '\n',
            'tool_calls': [
                {
                    'id': '1',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': {'cmd': 'cd /tmp && ls'}
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n'
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '\n',
            'tool_calls': [
                {
                    'id': '2',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': {'cmd': 'date'}
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '2',
            'content': '\n<pre>\nOUTPUT 2\n</pre>\n'
        }
    ]

    assert messages == expected_messages


def test_parse_chat_messages_with_deduplication(tmp_path):
    input = textwrap.dedent("""\
        **user>** Text 1

        **user>** Text 2

        **assistant>** Incomplete response

        **assistant>** Complete response
        """)
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

    expected_messages = [
        {
            'role': 'user',
            'name': 'user',
            'content': 'Text 1\n\n'
        },
        {
            'role': 'user',
            'name': 'user',
            'content': 'Text 2\n\n'
        },
        {
            'role': 'assistant',
            'name': 'assistant',
            'content': 'Complete response\n'
        }
    ]

    assert messages == expected_messages
