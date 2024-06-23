import textwrap

import pyparsing as pp
from pyparsing import LineStart

from taskmates.grammar.parsers.front_matter_parser import front_matter_parser
from taskmates.grammar.parsers.messages_parser import messages_parser

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")


def markdown_chat_parser():
    comments = pp.Suppress(LineStart() + pp.Literal("[//]: #") + pp.restOfLine)
    return (pp.Opt(front_matter_parser()) + messages_parser() + pp.StringEnd()).ignore(comments)


def test_no_line_end():
    input = textwrap.dedent("""\
        **user>** Short answer. 1+1=
        
        **assistant>** Short answer. 1+1=""")

    expected_messages = [{'content': 'Short answer. 1+1=\n\n',
                          'name': 'user'},
                         {'content': 'Short answer. 1+1=',
                          'name': 'assistant'}]

    results = markdown_chat_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == expected_messages


def test_markdown_with_tool_execution():
    input = textwrap.dedent("""\
        **assistant>** Here is a message.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user>** Here is another message.
        """)

    result = markdown_chat_parser().parseString(input)
    messages = [m.as_dict() for m in result.messages]
    assert messages == [
        {
            'content': 'Here is a message.\n\n',
            'name': 'assistant',
            'tool_calls': [
                {
                    'function': {
                        'arguments': {'cmd': 'cd /tmp'},
                        'name': 'run_shell_command'
                    },
                    'id': '1',
                    'type': 'function'
                }
            ]
        },
        {'content': '\n<pre>\nOUTPUT 1\n</pre>\n\n',
         'name': 'run_shell_command',
         'role': 'tool',
         'tool_call_id': '1'},
        {
            'content': 'Here is another message.\n',
            'name': 'user'
        }
    ]


def test_markdown_with_code_cell_execution():
    input = textwrap.dedent("""\
        print(1 + 1)
        
        **assistant>**
        
        print(1 + 1)
        
        ```python .eval
        print(1 + 1)
        ```

        ###### Cell Output: stdout [cell_0]
    
        <pre>
        2
        </pre>
    
        **assistant>** 
        
        1 + 1 equals 2.

        """)

    result = markdown_chat_parser().parseString(input)
    messages = [m.as_dict() for m in result.messages]
    assert messages == [
        {
            'content': 'print(1 + 1)\n\n', 'name': 'user'
        },
        {
            'content': '\n'
                       'print(1 + 1)\n'
                       '\n'
                       '```python .eval\n'
                       'print(1 + 1)\n'
                       '```\n'
                       '\n'
            ,
            'name': 'assistant'
        },
        {'code_cell_id': 'cell_0',
         'content': '\n<pre>\n2\n</pre>\n\n',
         'role': 'cell_output',
         'name': 'stdout'},
        {
            'content': '\n\n1 + 1 equals 2.\n\n',
            'name': 'assistant'
        }]


