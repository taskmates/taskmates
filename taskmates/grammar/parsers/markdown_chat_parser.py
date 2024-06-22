import textwrap

import pyparsing as pp
from pyparsing import LineStart

from taskmates.grammar.parsers.front_matter_parser import front_matter_parser
from taskmates.grammar.parsers.messages_parser import messages_parser


def markdown_chat_parser():
    comments = pp.Suppress(LineStart() + pp.Literal("[//]: #") + pp.restOfLine)
    return (pp.Opt(front_matter_parser()) + messages_parser() + pp.string_end).ignore(comments)


def test_markdown_chat_parser():
    input = textwrap.dedent("""\
        **assistant** Here is a message.
        
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp"}`
        
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user** Here is another message.
        """)

    result = markdown_chat_parser().parseString(input)
    messages = [m.as_dict() for m in result.messages]
    assert messages == [
        {
            'attributes': {},
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
            'attributes': {},
            'content': 'Here is another message.\n',
            'name': 'user'
        }
    ]
