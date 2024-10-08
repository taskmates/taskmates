import re
import textwrap

import pyparsing as pp

from taskmates.grammar.parsers.header.headers import headers_parser
from taskmates.grammar.parsers.message.code_cell_parser import code_cell_parser
from taskmates.grammar.parsers.message.pre_tag_parser import pre_tag_parser
from taskmates.grammar.parsers.message.tool_calls_parser import tool_calls_parser

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")

USERNAME = r"([a-zA-Z0-9_]+)"
JSON = r"(\{[^\}]+\})"
START_OF_CHAT_HEADER = fr"(\*\*{USERNAME}( {JSON})?>\*\*)"
END_OF_CHAT_HEADER = r"(>\*\*[ \n])"
END_OF_CHAT_HEADER_BEHIND = fr"((?<={END_OF_CHAT_HEADER}))"

BEGINING_OF_SECTION = fr"(^({START_OF_CHAT_HEADER}|```|<pre|</pre|###### (Steps|Execution|Cell Output)))"
NOT_BEGINNING_OF_SECTION_AHEAD = fr"(?!{BEGINING_OF_SECTION})"
END_OF_STRING = r"\Z"


def message_parser():
    message_content = message_content_parser()

    message = pp.Group(
        pp.LineStart()
        + headers_parser()
        + message_content
        + pp.Optional(tool_calls_parser())
    )
    return message


def message_content_parser():
    text_content = pp.Regex(fr"({NOT_BEGINNING_OF_SECTION_AHEAD}.)+", re.DOTALL | re.MULTILINE)
    code_cell = code_cell_parser()
    pre_tag = pre_tag_parser()
    return pp.Combine(
        (text_content | code_cell | pre_tag)[...]
    )("content")


def first_message_parser(implicit_role: str = "user"):
    message_content = message_content_parser()
    implicit_header = (pp.LineStart() + pp.Empty().setParseAction(lambda: implicit_role)("name"))
    first_message = pp.Group(
        (headers_parser() | implicit_header)
        + message_content
        + pp.Optional(tool_calls_parser())
    )
    return first_message


def messages_parser(implicit_role: str = "user"):
    first_message, message = first_message_parser(implicit_role=implicit_role), message_parser()
    messages = (first_message + message[...]).set_results_name("messages")

    return messages


def test_messages_parser_single_message():
    input = textwrap.dedent("""\
        **user>** Hello, assistant!
        
        This is a multiline message.

        """)

    expected_messages = [{'content': 'Hello, assistant!\n\nThis is a multiline message.\n\n',
                          'name': 'user'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_parser_with_false_positive():
    input = textwrap.dedent("""\
        **user>** Here is a message.
         
        **This one is not** a message
        
        **assistant>** Here is another message.
        """)

    expected_messages = [{'content': 'Here is a message.\n\n**This one is not** a message\n\n',
                          'name': 'user'},
                         {'content': 'Here is another message.\n',
                          'name': 'assistant'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_with_implicit_header():
    input = textwrap.dedent("""\
        Hello
        
        **assistant>** Hello
        """)

    expected_messages = [{'content': 'Hello\n\n',
                          'name': 'user'},
                         {'content': 'Hello\n',
                          'name': 'assistant'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_with_no_line_end():
    input = textwrap.dedent("""\
        **john>** Hello

        **alice>** Hello""")

    expected_messages = [{'content': 'Hello\n\n',
                          'name': 'john'},
                         {'content': 'Hello',
                          'name': 'alice'}]

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_messages_parser_mutiple_messages():
    input = textwrap.dedent("""\
        **user>** Hello, assistant!
        
        This is a multiline message.

        **assistant>** Hi, user!
        
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
        **assistant>** This is a message with multiple tool calls.
        
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
        **assistant>** This is a message with tool calls.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user>** Here is another message.
        
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


def test_messages_parser_with_multiple_tool_executions():
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

    expected_messages = [
        {
            'name': 'user',
            'content': 'USER INSTRUCTION\n\n'
        },
        {
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

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_code_cell_execution():
    input = textwrap.dedent("""\
        **user>** This is a message with code cells.
        
        ```python .eval
        print(1 + 1)
        ```
        
        ###### Cell Output: stdout [cell_0]
        
        <pre>
        2
        </pre>
        
        **assistant>** 1 + 1 equals 2.
        
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


def test_messages_parser_with_false_header_in_code_cell():
    input = textwrap.dedent('''\
        **user>** Here's a code block with a false header:

        ```python .eval
        print("""
        **assistant>** This is a false positive.
        """)
        ```

        **assistant>** This is a real message.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': 'Here\'s a code block with a false header:\n\n```python .eval\nprint("""\n**assistant>** This is a false positive.\n""")\n```\n\n'
        },
        {
            'name': 'assistant',
            'content': 'This is a real message.\n'
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_code_cell():
    input = textwrap.dedent('''\
        **user>** This is a message with code cells
        
        ```python .eval
        print("hello")
        ```
        
        ''')

    expected = textwrap.dedent('''\
        This is a message with code cells
        
        ```python .eval
        print("hello")
        ```
        
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': expected
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_code_cell_only_message():
    input = textwrap.dedent('''\
        ```python .eval
        print("hello")
        ```
        
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': input
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_code_cell_with_no_new_line():
    input = textwrap.dedent('''\
        ```python .eval
        print("hello")
        ```''')

    expected_messages = [
        {
            'name': 'user',
            'content': input
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_code_cell_with_no_language():
    input = textwrap.dedent('''\
        ```
        hello
        ```

        ```
        world
        ```
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': input
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_nested_code_cells():
    input = textwrap.dedent('''\
        ```markdown
        ```python .eval
        print("hello")
        ```
        ```shell .eval
        echo hello
        ```
        ```
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': input
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_false_header_in_pre_tag():
    input = textwrap.dedent('''\
        **user>** Here's a pre block with a false header:

        <pre>
        **assistant>** This is a false positive.
        </pre>

        **assistant>** This is a real message.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': 'Here\'s a pre block with a false header:\n\n<pre>\n**assistant>** This is a false positive.\n</pre>\n\n'
        },
        {
            'name': 'assistant',
            'content': 'This is a real message.\n'
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages
