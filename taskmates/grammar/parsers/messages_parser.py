import re
import textwrap
from dataclasses import dataclass
from typing import Optional, List

import pyparsing as pp
from pydantic import BaseModel
from pyparsing import ParseResults

from taskmates.grammar.parsers.header.headers import headers_parser
from taskmates.grammar.parsers.message.code_cell_parser import code_cell_parser, CodeCellNode
from taskmates.grammar.parsers.message.pre_tag_parser import pre_tag_parser
from taskmates.grammar.parsers.message.tool_calls_parser import tool_calls_parser

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")

USERNAME = r"([a-zA-Z0-9_]+)"
JSON = r"(\{[^\}]+\})"
START_OF_CHAT_HEADER = fr"(\*\*{USERNAME}( {JSON})?>\*\*)"
END_OF_CHAT_HEADER = r"(>\*\*[ \n])"
END_OF_CHAT_HEADER_BEHIND = fr"((?<={END_OF_CHAT_HEADER}))"

BEGINNING_OF_SECTION = fr"(^({START_OF_CHAT_HEADER}|```|<pre|</pre|###### (Steps|Execution|Cell Output)))"
NOT_BEGINNING_OF_SECTION_AHEAD = fr"(?!{BEGINNING_OF_SECTION})"
END_OF_STRING = r"\Z"


class MetaNode(BaseModel):
    key: str
    value: float

    @classmethod
    def from_tokens(cls, tokens: ParseResults):
        return cls(key=tokens.key, value=float(tokens.value))


def meta_line_parser():
    key = pp.Word(pp.alphas + '_')('key')
    value = pp.Word(pp.nums + '.')('value')
    meta_line = (
            pp.LineStart()
            + pp.Literal('[//]: # (meta:')
            + key
            + pp.Literal('=').suppress()
            + value
            + pp.Literal(')')
            + pp.LineEnd()
    ).set_parse_action(MetaNode.from_tokens)

    return meta_line


class MessageNode(BaseModel):
    name: str
    content: str
    role: Optional[str] = None
    code_cell_id: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list] = None
    attributes: Optional[dict] = None
    code_cells: Optional[List[CodeCellNode]] = None
    meta: Optional[List[MetaNode]] = None

    @classmethod
    def create(cls, s, loc, tokens: ParseResults):
        dct = tokens.as_dict()
        child_nodes = dct.pop("child_nodes")
        dct["content"] = "".join(n.source for n in child_nodes)
        dct["code_cells"] = [n for n in child_nodes if isinstance(n, CodeCellNode) and n.eval]
        if not dct["code_cells"]:
            del dct["code_cells"]
        return MessageNode(**dct)

    def as_dict(self):
        return self.model_dump(exclude_unset=True)


@dataclass
class TextContentNode:
    source: str

    @classmethod
    def from_tokens(cls, tokens):
        return cls(source=remove_comments(tokens[0]))


# Regular text content that's not inside special blocks
def remove_comments(text):
    lines = text.split('\n')
    filtered_lines = [line for line in lines if not line.strip().startswith('[//]: #')]
    return '\n'.join(filtered_lines)


def message_content_parser():
    # Code cells and pre tags (which should not ignore comments)
    code_cell = code_cell_parser()
    pre_tag = pre_tag_parser()

    text_content = (
        pp.Regex(fr"({NOT_BEGINNING_OF_SECTION_AHEAD}.)+", re.DOTALL | re.MULTILINE)
    ).set_parse_action(TextContentNode.from_tokens)

    return pp.Group(
        (text_content | code_cell | pre_tag)[...]
    )("child_nodes")


def first_message_parser(implicit_role: str = "user"):
    message_content = message_content_parser()
    implicit_header = (pp.LineStart() + pp.Empty().setParseAction(lambda: implicit_role)("name"))
    first_message = (
            (headers_parser() | implicit_header)
            + message_content
            + pp.Optional(tool_calls_parser())
    )
    return first_message.set_parse_action(MessageNode.create)


def message_parser():
    message_content = message_content_parser()

    message = (
            pp.LineStart()
            + headers_parser()
            + message_content
            + pp.Optional(tool_calls_parser())
    )
    return message.set_parse_action(MessageNode.create)


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


def test_messages_parser_multiple_messages():
    input = textwrap.dedent("""\
        **user>** Hello, assistant!
        
        This is a multiline message.

        **assistant>** Hi, user!
        
        This is the response.
        
        **user>** Hi again.
        
        This is a reply.
        """)

    results = messages_parser().parseString(input)

    assert [m.as_dict() for m in results.messages] == [
        {'content': 'Hello, assistant!\n\nThis is a multiline message.\n\n',
         'name': 'user'},
        {'content': 'Hi, user!\n\nThis is the response.\n\n', 'name': 'assistant'},
        {'content': 'Hi again.\n\nThis is a reply.\n', 'name': 'user'}]


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
            'code_cells': [{
                'source': '```python .eval\nprint(1 + 1)\n```\n',
                'content': 'print(1 + 1)\n',
                'language': 'python',
                'eval': True
            }]
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
            'content': 'Here\'s a code block with a false header:\n\n```python .eval\nprint("""\n**assistant>** This is a false positive.\n""")\n```\n\n',
            'code_cells': [{
                'source': '```python .eval\nprint("""\n**assistant>** This is a false positive.\n""")\n```\n',
                'content': 'print("""\n**assistant>** This is a false positive.\n""")\n',
                'language': 'python',
                'eval': True
            }]
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
            'content': expected,
            'code_cells': [{
                'source': '```python .eval\nprint("hello")\n```\n',
                'content': 'print("hello")\n',
                'language': 'python',
                'eval': True
            }]
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
            'content': input,
            'code_cells': [{'content': 'print("hello")\n',
                            'eval': True,
                            'language': 'python',
                            'source': '```python .eval\nprint("hello")\n```\n'}]
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
            'content': input,
            'code_cells': [{
                'source': '```python .eval\nprint("hello")\n```',
                'content': 'print("hello")\n',
                'language': 'python',
                'eval': True
            }]
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


def test_messages_parser_with_partial_code_cell():
    input = textwrap.dedent('''\
        **user>** First complete message.
        
        **assistant>** Incomplete message with unclosed code block
        
        ```python
        def hello():
        ''')

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages[0] == {
        'name': 'user',
        'content': 'First complete message.\n\n',
    }
    assert parsed_messages[1] == {
        'name': 'assistant',
        'content': 'Incomplete message with unclosed code block\n\n```python\ndef hello():\n',
    }


def test_messages_parser_with_partial_pre_tag():
    input = textwrap.dedent('''\
        **user>** First message
        
        **assistant>** Message with unclosed pre tag
        
        <pre>
        some content
        ''')

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert len(parsed_messages) == 2
    assert parsed_messages[0] == {
        'name': 'user',
        'content': 'First message\n\n',
    }
    assert parsed_messages[1] == {
        'name': 'assistant',
        'content': 'Message with unclosed pre tag\n\n<pre>\nsome content\n',
    }


def test_messages_parser_with_markdown_comments():
    input = textwrap.dedent('''\
        **user>** Here's a message with comments
        [//]: # (This comment should be ignored)
        
        ```python
        # This is a Python comment
        [//]: # (This comment should be preserved)
        print("hello")
        ```
        
        <pre>
        [//]: # (This comment should be preserved)
        Some content
        </pre>
        
        [//]: # (This comment should be ignored)
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Here's a message with comments\n\n"
                       "```python\n"
                       "# This is a Python comment\n"
                       "[//]: # (This comment should be preserved)\n"
                       'print("hello")\n'
                       "```\n\n"
                       "<pre>\n"
                       "[//]: # (This comment should be preserved)\n"
                       "Some content\n"
                       "</pre>\n\n"
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages

# TODO
# def test_messages_parser_with_invalid_metadata():
#     input = textwrap.dedent('''\
#         **user>** Here's a message with invalid metadata
#
#         This is the message content.
#
#         [//]: # (meta:invalid_format)
#         [//]: # (meta:temperature=invalid)
#         ''')
#
#     expected_messages = [
#         {
#             'name': 'user',
#             'content': "Here's a message with invalid metadata\n\nThis is the message content.\n\n[//]: # (meta:invalid_format)\n[//]: # (meta:temperature=invalid)\n"
#         }
#     ]
#
#     results = messages_parser().parseString(input)
#     parsed_messages = [m.as_dict() for m in results.messages]
#
#     assert parsed_messages == expected_messages
#
#
# def test_messages_parser_with_metadata_at_start():
#     input = textwrap.dedent('''\
#         **user>** [//]: # (meta:temperature=0.7)
#         [//]: # (meta:top_p=0.9)
#
#         Here's a message with metadata at the start.
#         ''')
#
#     expected_messages = [
#         {
#             'name': 'user',
#             'content': "\nHere's a message with metadata at the start.\n",
#             'meta': [
#                 {'key': 'temperature', 'value': 0.7},
#                 {'key': 'top_p', 'value': 0.9}
#             ]
#         }
#     ]
#
#     results = messages_parser().parseString(input)
#     parsed_messages = [m.as_dict() for m in results.messages]
#
#     assert parsed_messages == expected_messages
#
#
# def test_messages_parser_with_mixed_metadata():
#     input = textwrap.dedent('''\
#         **user>** Here's a message with mixed metadata
#
#         [//]: # (meta:temperature=0.7)
#         This is some content.
#         [//]: # (meta:top_p=0.9)
#         More content.
#         ''')
#
#     expected_messages = [
#         {
#             'name': 'user',
#             'content': "Here's a message with mixed metadata\n\nThis is some content.\nMore content.\n",
#             'meta': [
#                 {'key': 'temperature', 'value': 0.7},
#                 {'key': 'top_p', 'value': 0.9}
#             ]
#         }
#     ]
#
#     results = messages_parser().parseString(input)
#     parsed_messages = [m.as_dict() for m in results.messages]
#
#     assert parsed_messages == expected_messages
