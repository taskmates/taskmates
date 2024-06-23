import textwrap
from re import RegexFlag

import pyparsing as pp

from taskmates.grammar.parsers.message.header.chat_message_header_parser import chat_message_header_parser
from taskmates.grammar.parsers.message.header.code_cell_execution_header_parser import code_cell_execution_header_parser
from taskmates.grammar.parsers.message.header.tool_execution_header_parser import tool_execution_header_parser
from taskmates.grammar.parsers.message.tool_calls_parser import tool_calls_parser

pp.enable_all_warnings()

header_delimiter = pp.Suppress(pp.Literal("**"))

# message_entry = pp.Forward()

message_header = chat_message_header_parser()
tool_execution_header = tool_execution_header_parser()
code_cell_execution_header = code_cell_execution_header_parser()
message_tool_calls = tool_calls_parser()
headers = (message_header | tool_execution_header | code_cell_execution_header)

# TODO: This is really slow
# message_content = pp.SkipTo(message_tool_calls | message_entry | pp.stringEnd, include=False).leave_whitespace()(
#     "content")

# TODO: This is eagerly consuming other messages
# message_content = pp.Regex(".+?\n+(?=(?:(?:###### (?:Steps|Execution|(?:Cell Output))|(?:\*\*[^\n*]+\*\*))))",
#                            RegexFlag.DOTALL).leave_whitespace()("content")

# TODO: this breaks when content starts with a \n
# message_content = pp.Regex("[^\n].+?(\n*$|\n+(?=(?:\*\*|###### )))", RegexFlag.DOTALL).leave_whitespace()("content")

message_content = pp.Regex(".+?(\n*$|\n+(?=(?:\*\*|###### )))", RegexFlag.DOTALL).leave_whitespace()("content")


# message_content = pp.Regex("[^\n].+",
#                            RegexFlag.DOTALL).leave_whitespace()("content")

# message_content = pp.Regex("Hello, assistant!\n\nThis is a multiline message.\n\n",
#                            RegexFlag.DOTALL).leave_whitespace()("content")


# message_entry <<= pp.Group(
#     headers
#     + message_content
#     + pp.Optional(message_tool_calls))


def first_message_parser():
    # global message_entry

    # message_content = pp.SkipTo(message_tool_calls | message_entry | pp.stringEnd, include=False).leave_whitespace()(
    #     "content")
    implicit_message_header = (pp.line_start + pp.Empty().setParseAction(lambda: "user")("name"))
    first_message_headers = (headers | implicit_message_header)

    first_message = pp.Group(
        first_message_headers
        + message_content
        + pp.Optional(message_tool_calls))

    return first_message


def message_parser():
    # global message_entry
    #
    # return message_entry
    message = pp.Group(
        headers
        + message_content
        + pp.Optional(message_tool_calls))
    return message


def messages_parser():
    first_message = first_message_parser()
    message = message_parser()

    messages = (first_message
                + message[...]
                + pp.string_end).set_results_name("messages")

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
