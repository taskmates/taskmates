import textwrap

import pyparsing as pp

from taskmates.grammar.parsers.message.message_parser import message_parser, first_message_parser

pp.enable_all_warnings()

header_delimiter = pp.Suppress(pp.Literal("**"))


def messages_parser():
    first_message = first_message_parser()
    message = message_parser()

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
            'name': 'cell_output',
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
