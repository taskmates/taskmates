import textwrap
import time
from pathlib import Path
from typing import Tuple, List, Dict, Union

import pyparsing
from typeguard import typechecked

from taskmates.formats.markdown.processing.process_image_transclusion import render_image_transclusion
from taskmates.formats.openai.get_text_content import get_text_content
from taskmates.formats.openai.set_text_content import set_text_content
from taskmates.grammar.parsers.markdown_chat_parser import markdown_chat_parser
from taskmates.lib.markdown_.render_transclusions import render_transclusions
from taskmates.lib.root_path.root_path import root_path
from taskmates.logging import logger
from taskmates.workflow_engine.run import RUN


@typechecked
async def parse_front_matter_and_messages(source_file: Path,
                                          content: str,
                                          implicit_role: str) -> Tuple[
    List[Dict[str, Union[str, list[dict]]]], Dict[str, any]]:

    output_streams = RUN.get().signals["output_streams"]
    artifact_signals = output_streams.artifact

    transclusions_base_dir = source_file.parent

    messages: list[dict] = []

    start_time = time.time()  # Record the start time
    logger.debug(f"[parse_front_matter_and_messages] Parsing markdown: {start_time}-parsed-{source_file.name}")
    logger.debug("Markdown Content:\n" + content)

    parser = markdown_chat_parser(implicit_role=implicit_role)

    end_time = time.time()  # Record the end time
    time_taken = end_time - start_time
    logger.debug(
        f"[parse_front_matter_and_messages] Parsed markdown {start_time}-parsed-{source_file.name} in {time_taken:.4f} seconds")

    await artifact_signals.send_async(
        {"name": f"{start_time}-parsed-{source_file.name}", "content": content})

    try:
        parsed_chat = parser.parse_string(content)[0]
    except pyparsing.exceptions.ParseSyntaxException as e:
        await artifact_signals.send_async(
            {"name": f"[parse_front_matter_and_messages_error] {start_time}-parsed-{source_file.name}",
             "content": content})
        logger.error(f"Failed to parse markdown: ~/.taskmates/logs/{start_time}-parsed-{source_file.name}")
        logger.error(e)
        raise
    except pyparsing.exceptions.ParseException as e:
        await artifact_signals.send_async(
            {"name": f"[parse_front_matter_and_messages_error] {start_time}-parsed-{source_file.name}",
             "content": content})
        logger.error(f"Failed to parse markdown: ~/.taskmates/logs/{start_time}-parsed-{source_file.name}")
        logger.error(e)
        raise
    front_matter = parsed_chat.front_matter or {}

    # If the front_matter contains a `system` key, prepend it as the system message
    if 'system' in front_matter:
        messages = [{"role": "system", "content": front_matter['system']}] + messages

    for parsed_message in parsed_chat.messages:
        message_dict = parsed_message.as_dict()

        meta = message_dict.get("meta")

        name = message_dict["name"]
        attributes = message_dict.get("attributes", {})

        message = {**({"role": message_dict["role"]} if "role" in message_dict else {}),
                   "name": name,
                   "content": message_dict["content"],
                   **({"code_cell_id": message_dict["code_cell_id"]} if "code_cell_id" in message_dict else {}),
                   **({"tool_call_id": message_dict["tool_call_id"]} if "tool_call_id" in message_dict else {}),
                   **attributes}

        if "tool_calls" in message_dict:
            message["tool_calls"] = message_dict["tool_calls"]

        if "code_cells" in message_dict:
            message["code_cells"] = message_dict["code_cells"]

        text_content = get_text_content(message_dict)

        # transclusions
        text_content = render_transclusions(text_content, source_file=source_file)

        # image_transclusion
        text_content = render_image_transclusion(text_content, transclusions_base_dir=transclusions_base_dir)

        set_text_content(message, text_content)

        messages.append(message)

    # set message roles based on the name
    for message in messages:
        if "role" in message:
            continue
        name = message.get("name", "user")
        # The role should match the name for user/assistant/system/tool messages
        if name in ("user", "assistant", "system", "tool"):
            message["role"] = name
        else:
            # For any other name, default to user role
            message["role"] = "user"

    for message in messages:
        if message.get("role") == "cell_output":
            output_name = message["name"]
            message["name"] = "cell_output"
            message["role"] = "user"
            set_text_content(message,
                             f"###### Cell Output: {output_name} [{message['code_cell_id']}]\n"
                             + get_text_content(message))

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


import pytest


@pytest.mark.asyncio
async def test_parse_chat_messages_with_internal_header(tmp_path):
    input = """\
        **user>** Here is a message.
         
        **This one is not** a message
        
        **assistant>** Here is another message.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n**This one is not** a message\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is another message.\n'}
    ]
    assert messages == expected_messages


@pytest.mark.asyncio
async def test_parse_chat_messages_with_frontmatter(tmp_path):
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
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    expected_front_matter = {'key1': 'value1', 'key2': ['item1', 'item2']}
    assert messages == expected_messages and front_matter == expected_front_matter


@pytest.mark.asyncio
async def test_parse_chat_messages_with_metadata(tmp_path):
    input = """\
        **user {"name": "john", "age": 30}>** Here is a message from John.
        
        **assistant {"model": "gpt-3.5-turbo"}>** Here is a response from the assistant.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Here is a message from John.\n\n'
    assert messages[0]['name'] == 'john'
    assert messages[0]['age'] == 30
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['content'] == 'Here is a response from the assistant.\n'
    assert messages[1]['model'] == 'gpt-3.5-turbo'


@pytest.mark.asyncio
async def test_parse_chat_messages_with_system_in_frontmatter(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 3
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == 'Here is a message.\n\n'
    assert messages[2]['role'] == 'assistant'
    assert messages[2]['content'] == 'Here is a response.\n'


@pytest.mark.asyncio
async def test_parse_chat_messages_with_system_in_frontmatter_and_content(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **system>** This is a system message from the content.
        
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 4
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'This is a system message from the front matter.'
    assert messages[1]['role'] == 'system'
    assert messages[1]['content'] == 'This is a system message from the content.\n\n'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'Here is a message.\n\n'
    assert messages[3]['role'] == 'assistant'
    assert messages[3]['content'] == 'Here is a response.\n'


@pytest.mark.asyncio
async def test_parse_chat_messages_with_tool_calls_and_execution(tmp_path):
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

    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")

    assert messages == expected_messages


@pytest.mark.asyncio
async def test_parse_chat_messages_with_multiple_tool_calls_and_missing_execution(tmp_path):
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
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

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


@pytest.mark.asyncio
async def test_parse_chat_messages_with_multiple_tool_calls_in_separate_messages(tmp_path):
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
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

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


@pytest.mark.asyncio
async def test_parse_chat_messages_with_deduplication(tmp_path):
    input = textwrap.dedent("""\
        **user>** Text 1

        **user>** Text 2

        **assistant>** Incomplete response

        **assistant>** Complete response
        """)
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", input, "user")

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


@pytest.mark.asyncio
async def test_parse_chat_messages_with_text_transclusion(tmp_path):
    transcluded_file = tmp_path / "transcluded_content.md"
    transcluded_file.write_text("This is transcluded content.\nIt should appear in the parsed message.")

    input = f"""\
        **user>** Here is a message with transclusion.
        
        #[[{transcluded_file}]]
        
        **assistant>** Here is a response.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    expected_messages = [
        {'role': 'user', 'name': 'user',
         'content': f'Here is a message with transclusion.\n\nThe following are the contents of the file {transcluded_file}:\n\n""""\nThis is transcluded content.\nIt should appear in the parsed message.\n""""\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    assert messages == expected_messages


@pytest.mark.asyncio
async def test_parse_chat_messages_with_image_transclusion(tmp_path):
    image_file = root_path() / "tests/fixtures/image.jpg"

    input = f"""\
        **user>** Here is a message with image transclusion.
        
        ![[{image_file}]]
        
        **assistant>** Here is a response.
        """
    messages, front_matter = await parse_front_matter_and_messages(tmp_path / "main.md", textwrap.dedent(input), "user")
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['name'] == 'user'
    assert isinstance(messages[0]['content'], list)
    assert messages[0]['content'][0]['type'] == 'text'
    assert messages[0]['content'][0]['text'] == f'Here is a message with image transclusion.\n\n![[{image_file}]]\n\n'
    assert messages[0]['content'][1]['type'] == 'image_url'
    assert messages[0]['content'][1]['image_url']['url'].startswith('data:image/jpg;base64,')
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['name'] == 'assistant'
    assert messages[1]['content'] == 'Here is a response.\n'
