import re
import textwrap

import pyparsing as pp

from taskmates.grammar.parsers.header.headers import headers_parser
from taskmates.grammar.parsers.message.tool_calls_parser import tool_calls_parser
from taskmates.grammar.parsers.section_start_anchor import section_start_anchor

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")


def message_parser():
    message_content = pp.Combine(
            pp.Regex(r"((((?<!^)(?<=\*\* )[^\n]*)|(^(?!(\*\*|###### ))[^\n]*))\n)+", re.DOTALL | re.MULTILINE) +
            pp.SkipTo(
                (section_start_anchor() + (tool_calls_parser() | headers_parser()) | pp.StringEnd()
                 ),
                include=False))("content")

    message = pp.Group(
        pp.LineStart()
        + headers_parser()
        + message_content
        + pp.Optional(tool_calls_parser())
    )
    return message


def first_message_parser():
    message_content = (pp.SkipTo(
        (section_start_anchor() + (tool_calls_parser() | headers_parser()) | pp.StringEnd()),
        include=False)("content"))
    implicit_header = (pp.LineStart() + pp.Empty().setParseAction(lambda: "user")("name"))
    first_message = pp.Group(
        (headers_parser() | implicit_header)
        + message_content
        + pp.Optional(tool_calls_parser())
    )
    return first_message


def messages_parser():
    first_message, message = first_message_parser(), message_parser()
    messages = (first_message + message[...]).set_results_name("messages")

    return messages


def test_messages_parser_single_message():
    input = textwrap.dedent("""\
        **user** Hello, assistant!
        
        This is a multiline message.

        """)

    expected_messages = [{'content': 'Hello, assistant!\n\nThis is a multiline message.\n\n',
                          'name': 'user'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_parser_mutiple_messages():
    input = textwrap.dedent("""\
        **user** Hello, assistant!
        
        This is a multiline message.

        **assistant** Hi, user!
        
        This is the response.
        """)

    expected_messages = [{'content': 'Hello, assistant!\n\nThis is a multiline message.\n\n',
                          'name': 'user'},
                         {'content': 'Hi, user!\n\nThis is the response.\n',
                          'name': 'assistant'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_parser_with_multiple_tool_calls():
    input = textwrap.dedent("""\
        **assistant** This is a message with multiple tool calls.
        
        ###### Steps
        
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        - Create File [2] `{"filename":"test.txt", "content":"Hello, World!"}`
        - Read File [3] `{"filename":"test.txt"}`
        
        """)
    expected_messages = [{'content': 'This is a message with multiple tool calls.\n\n',
                          'name': 'assistant',
                          'tool_calls': [
                              {
                                  "id": "1",
                                  "type": "function",
                                  "function": {
                                      "name": "run_shell_command",
                                      "arguments": {
                                          "cmd": "cd /tmp"
                                      }
                                  }
                              },
                              {
                                  "id": "2",
                                  "type": "function",
                                  "function": {
                                      "name": "create_file",
                                      "arguments": {
                                          "filename": "test.txt",
                                          "content": "Hello, World!"
                                      }
                                  }
                              },
                              {
                                  "id": "3",
                                  "type": "function",
                                  "function": {
                                      "name": "read_file",
                                      "arguments": {
                                          "filename": "test.txt"
                                      }
                                  }
                              }
                          ]}]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_tool_execution():
    input = textwrap.dedent("""\
        **assistant** This is a message with tool calls.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user** Here is another message.
        
        """)

    expected_messages = [
        {
            'content': 'This is a message with tool calls.\n\n',
            'name': 'assistant',
            'tool_calls': [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "run_shell_command",
                        "arguments": {
                            "cmd": "cd /tmp"
                        }
                    }
                },
            ]
        }, {
            'role': 'tool',
            'name': 'run_shell_command',
            'tool_call_id': '1',
            'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n'
        },
        {
            'name': 'user',
            'content': 'Here is another message.\n\n'
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_code_cell_execution():
    input = textwrap.dedent("""\
        **user** This is a message with code cells.
        
        ```python .eval
        print(1 + 1)
        ```
        
        ###### Cell Output: stdout [cell_0]
        
        <pre>
        2
        </pre>
        
        **assistant** 1 + 1 equals 2.
        
        """)

    expected_messages = [
        {
            'content': 'This is a message with code cells.\n'
                       '\n'
                       '```python .eval\n'
                       'print(1 + 1)\n'
                       '```\n'
                       '\n',
            'name': 'user',
        }, {
            'role': 'cell_output',
            'name': 'stdout',
            'code_cell_id': 'cell_0',
            'content': '\n<pre>\n2\n</pre>\n\n'
        },
        {
            'name': 'assistant',
            'content': '1 + 1 equals 2.\n\n'
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_single_message_with_implicit_header():
    input = textwrap.dedent("""\
        Hello, assistant!
        
        This is a multiline message.

        """)

    expected_messages = [{'content': 'Hello, assistant!\n\nThis is a multiline message.\n\n',
                          'name': 'user'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages
