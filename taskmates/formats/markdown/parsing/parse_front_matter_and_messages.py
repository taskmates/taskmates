import json
import re
import textwrap
from pathlib import Path
from typing import Tuple, List, Dict, Union

from typeguard import typechecked

from taskmates.formats.markdown.parsing.parse_front_matter_and_content import parse_front_matter_and_content
from taskmates.formats.markdown.parsing.substitute_tool_calls import substitute_tool_calls
from taskmates.formats.markdown.parsing.substitute_usernames import substitute_usernames
from taskmates.formats.markdown.processing.filter_comments import filter_comments
from taskmates.formats.markdown.processing.process_image_transclusion import render_image_transclusion
from taskmates.lib.markdown_.render_transclusions import render_transclusions

HEADER_PATTERN = r'^\*\*([a-z_0-9]+)(?: (.*?))?\*\*(?: )?'


@typechecked
def parse_front_matter_and_messages(source_file: Path,
                                    content: str,
                                    implicit_role: str) -> Tuple[
    List[Dict[str, Union[str, list[dict]]]], Dict[str, any]]:
    transclusions_base_dir = source_file.parent

    # remove comments
    content = filter_comments(content)

    front_matter, content = parse_front_matter_and_content(content)

    # prepend **user**
    if not content.lstrip().startswith("**"):
        content = f"**{implicit_role}**\n" + content.lstrip()

    # TODO: move this into the loop below
    content = substitute_usernames(content)

    messages: list[dict] = []

    # If the front_matter contains a `system` key, prepend it as the system message
    if 'system' in front_matter:
        messages = [{"role": "system", "content": front_matter['system']}] + messages

    # Define a regular expression pattern for chat message headers
    header_pattern = re.compile(HEADER_PATTERN, re.MULTILINE)

    # Find all headers in the chat content
    headers = [match for match in header_pattern.finditer(content)]

    # Split the content into messages by headers
    global_tool_call_id = 1
    for i in range(len(headers)):
        # Extract role and attributes from the header
        header_content = headers[i].group()
        role, attributes = re.match(HEADER_PATTERN, header_content).groups()

        message = {"role": role}

        start_index = headers[i].end()
        # If it's not the last header, the end index is the start of the next header - len("\n")
        end_index = (headers[i + 1].start() - len("\n")) if i + 1 < len(headers) else len(content)

        # Extract the message content
        text_content = content[start_index:end_index].lstrip("\n")

        # transclusions
        text_content = render_transclusions(text_content, source_file=source_file)

        # tool_calls
        tool_calls, text_content = substitute_tool_calls(text_content)
        if tool_calls:
            for tool_call in tool_calls:
                tool_call['id'] = str(global_tool_call_id)
                global_tool_call_id += 1
            message["tool_calls"] = tool_calls
            message["role"] = "assistant"

        # image_transclusion
        transcluded_content = render_image_transclusion(text_content, transclusions_base_dir=transclusions_base_dir)
        message["content"] = transcluded_content

        if attributes:
            # Parse attributes as JSON if they exist
            attributes_dict = json.loads(attributes)
            message.update(attributes_dict)
        messages.append(message)

    # set assistant roles
    for message in messages:
        if not message.get("name") or message['role'] == "tool":
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


def test_header_pattern_regex():
    header = "**user** Here is a message from John."
    match = re.match(HEADER_PATTERN, header)
    assert match is not None
    # Expecting no third group since we're not interested in capturing the message part
    assert match.groups() == ('user', None)

    header_with_attributes = "**user** {\"name\": \"john\", \"age\": 30}"
    match = re.match(HEADER_PATTERN, header_with_attributes)
    assert match is not None
    # The second group should capture the attributes, and there's no third group
    assert match.groups() == ('user', None)


def test_parse_chat_messages_with_internal_header(tmp_path):
    input = """\
        **user** Here is a message.
         
        **This one is not** a message
        
        **assistant** Here is another message.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n**This one is not** a message\n'},
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
        **user** Here is a message.
        
        **assistant** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    expected_front_matter = {'key1': 'value1', 'key2': ['item1', 'item2']}
    assert messages == expected_messages and front_matter == expected_front_matter


def test_parse_chat_messages_with_metadata(tmp_path):
    input = """\
        **user {"name": "john", "age": 30}** Here is a message from John.
        
        **assistant {"model": "gpt-3.5-turbo"}** Here is a response from the assistant.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Here is a message from John.\n'
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
        **user** Here is a message.
        
        **assistant** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 3
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == 'Here is a message.\n'
    assert messages[2]['role'] == 'assistant'
    assert messages[2]['content'] == 'Here is a response.\n'


def test_parse_chat_messages_with_system_in_frontmatter_and_content(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **system** This is a system message from the content.
        
        **user** Here is a message.
        
        **assistant** Here is a response.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 4
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'system'
    assert messages[1]['content'] == 'This is a system message from the content.\n'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'Here is a message.\n'
    assert messages[3]['role'] == 'assistant'
    assert messages[3]['content'] == 'Here is a response.\n'


def test_parse_chat_messages_with_tool_calls_and_execution(tmp_path):
    input = """\
        **assistant** Here is a message.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1] 
        
        <pre>
        OUTPUT 1
        </pre>
        
        
        **user** Here is another message.
        """
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 3
    assert messages[0]['role'] == 'assistant'
    assert messages[0]['content'] == 'Here is a message.\n'
    assert messages[1]['role'] == 'tool'
    assert messages[1]['name'] == 'run_shell_command'
    assert messages[1]['tool_call_id'] == '1'
    assert messages[1]['content'] == '<pre>\nOUTPUT 1\n</pre>\n\n'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'Here is another message.\n'


def test_parse_chat_messages_with_multiple_tool_calls_and_missing_execution(tmp_path):
    input = textwrap.dedent("""\
        USER INSTRUCTION
        
        **shell**
        
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
            'content': textwrap.dedent("""\
                USER INSTRUCTION
                """)
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '',
            'tool_calls': [
                {
                    'id': '1',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': '{"cmd": "cd /tmp && ls"}'
                    }
                },
                {
                    'id': '2',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': '{"cmd": "date"}'
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '<pre>\nOUTPUT 1\n</pre>\n'
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '2',
            'content': '<pre>\nOUTPUT 2\n</pre>\n'
        }
    ]

    assert messages == expected_messages


def test_parse_chat_messages_with_multiple_tool_calls_in_separate_messages(tmp_path):
    input = textwrap.dedent("""\
        USER INSTRUCTION
        
        **shell**
        
        ###### Steps
        
        - Run Shell Command [1] `{"cmd": "cd /tmp && ls"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **shell**
        
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
            'content': textwrap.dedent("""\
                USER INSTRUCTION
                """)
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '',
            'tool_calls': [
                {
                    'id': '1',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': '{"cmd": "cd /tmp && ls"}'
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '<pre>\nOUTPUT 1\n</pre>\n'
        },
        {
            'role': 'user',
            'name': 'shell',
            'content': '',
            'tool_calls': [
                {
                    'id': '2',
                    'type': 'function',
                    'function': {
                        'name': 'run_shell_command',
                        'arguments': '{"cmd": "date"}'
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '2',
            'content': '<pre>\nOUTPUT 2\n</pre>\n'
        }
    ]

    assert messages == expected_messages


def test_parse_chat_messages_with_deduplication(tmp_path):
    input = textwrap.dedent("""\
        **user** Text 1
        
        **user** Text 2
        
        **assistant** Incomplete response
        
        **assistant** Complete response
        """)
    messages, front_matter = parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

    expected_messages = [
        {
            'role': 'user',
            'name': 'user',
            'content': 'Text 1\n'
        },
        {
            'role': 'user',
            'name': 'user',
            'content': 'Text 2\n'
        },
        {
            'role': 'assistant',
            'name': 'assistant',
            'content': 'Complete response\n'
        }
    ]

    assert messages == expected_messages
