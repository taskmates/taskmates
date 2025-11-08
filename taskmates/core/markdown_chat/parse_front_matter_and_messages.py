import os
import textwrap
import time
from pathlib import Path
from typing import Tuple, List, Dict, Union

import pyparsing
from typeguard import typechecked

from taskmates.core.chat.openai.get_text_content import get_text_content
from taskmates.core.chat.openai.set_text_content import set_text_content
from taskmates.core.markdown_chat.grammar.parsers.markdown_chat_parser import markdown_chat_parser
from taskmates.core.markdown_chat.processing.process_image_transclusion import render_image_transclusion
from taskmates.lib.digest_.get_digest import get_digest
from taskmates.lib.markdown_.render_transclusions import render_transclusions
from taskmates.lib.root_path.root_path import root_path
from taskmates.logging import logger, file_logger


@typechecked
def parse_front_matter_and_messages(content: str,
                                    path: Union[str, Path] | None,
                                    default_sender: str = "user") -> Tuple[
    Dict[str, any],
    List[Dict[str, Union[str, list[dict]]]]
]:
    logger.debug("Parsing markdown structure")

    if path is None:
        path = Path(os.getcwd()) / f"{get_digest(path)}.md"
    path = Path(path)

    transclusions_base_dir = path.parent

    messages: list[dict] = []

    start_time = time.time()  # Record the start time
    logger.debug(f"[parse_front_matter_and_messages] Parsing markdown: {start_time}-parsed-{path.name}")
    logger.debug("Markdown Content:\n" + content)

    parser = markdown_chat_parser(implicit_role=default_sender)

    end_time = time.time()  # Record the end time
    time_taken = end_time - start_time
    logger.debug(
        f"[parse_front_matter_and_messages] Parsed markdown {start_time}-parsed-{path.name} in {time_taken:.4f} seconds")

    file_logger.debug(f"{start_time}-parsed-{path.name}", content=content)

    try:
        parsed_chat = parser.parse_string(content)[0]
    except pyparsing.exceptions.ParseSyntaxException as e:
        file_logger.debug(f"[parse_front_matter_and_messages_error] {start_time}-parsed-{path.name}",
                          content=content)
        logger.error(f"Failed to parse markdown: ~/.taskmates/logs/{start_time}-parsed-{path.name}")
        logger.error(e)
        raise
    except pyparsing.exceptions.ParseException as e:
        file_logger.debug(f"[parse_front_matter_and_messages_error] {start_time}-parsed-{path.name}",
                          content=content)
        logger.error(f"Failed to parse markdown: ~/.taskmates/logs/{start_time}-parsed-{path.name}")
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
        meta = message_dict.get("meta", {})

        message = {**({"role": message_dict["role"]} if "role" in message_dict else {}),
                   "name": name,
                   "content": message_dict["content"],
                   **({"code_cell_id": message_dict["code_cell_id"]} if "code_cell_id" in message_dict else {}),
                   **({"tool_call_id": message_dict["tool_call_id"]} if "tool_call_id" in message_dict else {}),
                   **attributes,
                   **({"meta": meta} if meta else {})}

        if "tool_calls" in message_dict:
            message["tool_calls"] = message_dict["tool_calls"]

        if "code_cells" in message_dict:
            message["code_cells"] = message_dict["code_cells"]

        text_content = get_text_content(message_dict)

        # transclusions
        text_content = render_transclusions(text_content, source_file=path)

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

    return front_matter, messages


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
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
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
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
    expected_messages = [
        {'role': 'user', 'name': 'user', 'content': 'Here is a message.\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    expected_front_matter = {'key1': 'value1', 'key2': ['item1', 'item2']}
    assert messages == expected_messages and front_matter == expected_front_matter


def test_parse_chat_messages_with_metadata(tmp_path):
    input = """\
        **user {"name": "john", "age": 30}>** Here is a message from John.
        
        **assistant {"model": "gpt-4o-mini"}>** Here is a response from the assistant.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Here is a message from John.\n\n'
    assert messages[0]['name'] == 'john'
    assert messages[0]['age'] == 30
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['content'] == 'Here is a response from the assistant.\n'
    assert messages[1]['model'] == 'gpt-4o-mini'


def test_parse_chat_messages_with_system_in_frontmatter(tmp_path):
    input = """\
        ---
        system: This is a system message from the front matter.
        ---
        **user>** Here is a message.
        
        **assistant>** Here is a response.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
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
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
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

    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")

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
    front_matter, messages = parse_front_matter_and_messages(input, tmp_path / "main.md", "user")

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
    front_matter, messages = parse_front_matter_and_messages(input, tmp_path / "main.md", "user")

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
    front_matter, messages = parse_front_matter_and_messages(input, tmp_path / "main.md", "user")

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


def test_parse_chat_messages_with_text_transclusion(tmp_path):
    transcluded_file = tmp_path / "transcluded_content.md"
    transcluded_file.write_text("This is transcluded content.\nIt should appear in the parsed message.")

    input = f"""\
        **user>** Here is a message with transclusion.
        
        #[[{transcluded_file}]]
        
        **assistant>** Here is a response.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
    expected_messages = [
        {'role': 'user', 'name': 'user',
         'content': f'Here is a message with transclusion.\n\nThe following are the contents of the file {transcluded_file}:\n\n""""\nThis is transcluded content.\nIt should appear in the parsed message.\n""""\n\n'},
        {'role': 'assistant', 'name': 'assistant', 'content': 'Here is a response.\n'}
    ]
    assert messages == expected_messages


def test_parse_chat_messages_with_image_transclusion(tmp_path):
    image_file = root_path() / "tests/fixtures/image.jpg"

    input = f"""\
        **user>** Here is a message with image transclusion.
        
        ![[{image_file}]]
        
        **assistant>** Here is a response.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")
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


def test_parse_chat_messages_with_html_meta_tags(tmp_path):
    input = """\
        **user>** Message with HTML meta tags
        
        <meta name="priority" content="high" />
        <meta name="category" content="support" />
        
        Some content after meta tags.
        
        **assistant>** Response message
        
        <meta name="model" content="gpt-4" />
        
        Response content.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")

    assert len(messages) == 2

    # Check user message with meta tags
    assert messages[0]['role'] == 'user'
    assert messages[0]['name'] == 'user'
    assert messages[0]['content'] == 'Message with HTML meta tags\n\n\nSome content after meta tags.\n\n'
    # Meta attributes should be under 'meta' key
    assert messages[0]['meta']['priority'] == 'high'
    assert messages[0]['meta']['category'] == 'support'

    # Check assistant message with meta tag
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['name'] == 'assistant'
    assert messages[1]['content'] == 'Response message\n\n\nResponse content.\n'
    assert messages[1]['meta']['model'] == 'gpt-4'


def test_parse_chat_messages_with_mixed_metadata_formats(tmp_path):
    input = """\
        **user>** Message with mixed metadata
        
        <meta name="author" content="John Doe" />
        [//]: # (meta:temperature = 0.7)
        <meta charset="UTF-8" />
        [//]: # (meta:max_tokens = 500)
        
        Content here.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")

    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['name'] == 'user'
    assert messages[0]['content'] == 'Message with mixed metadata\n\n\nContent here.\n'
    # Check all metadata is under 'meta' key
    assert messages[0]['meta']['author'] == 'John Doe'
    assert messages[0]['meta']['temperature'] == 0.7
    assert messages[0]['meta']['charset'] == 'UTF-8'
    assert messages[0]['meta']['max_tokens'] == 500


def test_parse_chat_messages_with_meta_in_code_blocks(tmp_path):
    input = """\
        **user>** Meta tags in code blocks should not be parsed
        
        ```html
        <meta name="viewport" content="width=device-width" />
        ```
        
        <meta name="real" content="metadata" />
        
        Done.
        """
    front_matter, messages = parse_front_matter_and_messages(textwrap.dedent(input), tmp_path / "main.md", "user")

    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['name'] == 'user'
    # Meta tag in code block should be preserved in content
    assert '<meta name="viewport"' in messages[0]['content']
    # Only the real meta tag outside code block should be parsed and stored under 'meta' key
    assert messages[0]['meta']['real'] == 'metadata'
