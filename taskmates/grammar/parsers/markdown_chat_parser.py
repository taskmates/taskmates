import textwrap
from typing import Optional

import pyparsing as pp
from pydantic import BaseModel
from pyparsing import ParseResults

from taskmates.grammar.parsers.front_matter_parser import front_matter_parser
from taskmates.grammar.parsers.messages_parser import messages_parser, MessageNode

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")


class ChatNode(BaseModel):
    front_matter: Optional[dict] = None
    messages: list[MessageNode]

    @classmethod
    def from_tokens(cls, tokens: ParseResults):
        tokens.as_list()
        tokens["messages"].as_list()
        return cls(**tokens.as_dict())

    def as_dict(self):
        return self.model_dump(exclude_unset=True)


def markdown_chat_parser(implicit_role: str = "user"):
    return (pp.Opt(front_matter_parser())
            + messages_parser(implicit_role=implicit_role)
            + pp.StringEnd()).set_parse_action(ChatNode.from_tokens)


def test_no_line_end():
    input = textwrap.dedent("""\
        **user>** Short answer. 1+1=
        
        **assistant>** Short answer. 1+1=""")

    expected_messages = [{'content': 'Short answer. 1+1=\n\n',
                          'name': 'user'},
                         {'content': 'Short answer. 1+1=',
                          'name': 'assistant'}]

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == expected_messages


def test_with_front_matter():
    input = textwrap.dedent("""\
        ---
        key1: value1
        key2:
          - item1
          - item2
        ---
        
        **user>** Message
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results == {
        'front_matter': {'key1': 'value1', 'key2': ['item1', 'item2']},
        'messages': [{'content': 'Message\n', 'name': 'user'}]
    }


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

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
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


def test_markdown_with_code_cell():
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
    
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
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
            'name': 'assistant',
            'code_cells': [{
                'source': '```python .eval\nprint(1 + 1)\n```\n',
                'content': 'print(1 + 1)\n',
                'language': 'python',
                'eval': True
            }]
        },
        {'code_cell_id': 'cell_0',
         'content': '\n<pre>\n2\n</pre>\n\n',
         'role': 'cell_output',
         'name': 'stdout'},
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

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
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
            'name': 'assistant',
            'code_cells': [{
                'source': '```python .eval\nprint(1 + 1)\n```\n',
                'content': 'print(1 + 1)\n',
                'language': 'python',
                'eval': True
            }]
        },
        {'code_cell_id': 'cell_0',
         'content': '\n<pre>\n2\n</pre>\n\n',
         'role': 'cell_output',
         'name': 'stdout'},
        {
            'content': '\n\n1 + 1 equals 2.\n\n',
            'name': 'assistant'
        }]


def test_markdown_comments_outside_code_blocks():
    input = textwrap.dedent("""\
        **user>** Here's a message with a comment.
        [//]: # (This comment should be ignored)
        
        **assistant>** Here's another message.
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
        {
            'content': "Here's a message with a comment.\n\n",
            'name': 'user'
        },
        {
            'content': "Here's another message.\n",
            'name': 'assistant'
        }
    ]


def test_markdown_comments_inside_code_blocks():
    input = textwrap.dedent("""\
        **user>** Here's a code block with a comment:
        
        ```python
        # This is a Python comment
        [//]: # (This comment should be preserved)
        print("Hello")
        ```
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
        {
            'content': "Here's a code block with a comment:\n\n"
                       "```python\n"
                       "# This is a Python comment\n"
                       "[//]: # (This comment should be preserved)\n"
                       'print("Hello")\n'
                       "```\n",
            'name': 'user'
        }
    ]


def test_markdown_comments_inside_pre_tags():
    input = textwrap.dedent("""\
        **user>** Here's a pre block with a comment:
        
        <pre>
        [//]: # (This comment should be preserved)
        Some content
        </pre>
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [
        {
            'content': "Here's a pre block with a comment:\n\n"
                       "<pre>\n"
                       "[//]: # (This comment should be preserved)\n"
                       "Some content\n"
                       "</pre>\n",
            'name': 'user'
        }
    ]


def test_special_chars():
    input = textwrap.dedent("""\
        Special char
                
        ###### Cell Output: stdout [cell_0]
        
        <pre>
            Special char: ·
        </pre>
        """)

    results = markdown_chat_parser().parseString(input)[0].as_dict()

    assert results["messages"] == [{'content': 'Special char\n\n', 'name': 'user'},
                                   {'code_cell_id': 'cell_0',
                                    'content': '\n<pre>\n    Special char: ·\n</pre>\n',
                                    'name': 'stdout',
                                    'role': 'cell_output'}]
