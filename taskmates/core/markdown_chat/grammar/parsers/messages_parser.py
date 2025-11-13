import re
import textwrap
from dataclasses import dataclass
from typing import Optional, List, Any

import pyparsing as pp
import pytest
from pydantic import BaseModel
from pyparsing import ParseResults

from taskmates.core.markdown_chat.grammar.parsers.header.headers_parser import headers_parser
from taskmates.core.markdown_chat.grammar.parsers.message.code_cell_parser import code_cell_parser, CodeCellNode
from taskmates.core.markdown_chat.grammar.parsers.message.pre_tag_parser import pre_tag_parser, PreBlockNode
from taskmates.core.markdown_chat.grammar.parsers.message.meta_tag_parser import meta_tag_parser, MetaTagNode
from taskmates.core.markdown_chat.grammar.parsers.message.tool_calls_parser import tool_calls_parser

pp.enable_all_warnings()
pp.ParserElement.set_default_whitespace_chars("")

USERNAME = r"([a-zA-Z0-9_]+)"
JSON = r"(\{[^\}]+\})"
START_OF_CHAT_HEADER = fr"(\*\*{USERNAME}( {JSON})?>\*\*)"
END_OF_CHAT_HEADER = r"(>\*\*[ \n])"
END_OF_CHAT_HEADER_BEHIND = fr"((?<={END_OF_CHAT_HEADER}))"

BEGINNING_OF_SECTION = fr"(^({START_OF_CHAT_HEADER}|```|<pre|</pre|<meta|###### (Steps|Execution|Cell Output)|(\[//\]: #)))"
NOT_BEGINNING_OF_SECTION_AHEAD = fr"(?!{BEGINNING_OF_SECTION})"
END_OF_STRING = r"\Z"


@dataclass
class TextContentNode:
    source: str

    @classmethod
    def from_tokens(cls, tokens):
        return cls(source=tokens[0])


@dataclass
class CommentNode:
    source: str

    @classmethod
    def from_tokens(cls, tokens):
        return cls(source=tokens[0])


class MetaNode(BaseModel):
    key: str
    value: Any

    @classmethod
    def from_tokens(cls, tokens: ParseResults):
        meta_str = tokens.meta_str.strip()

        # Extract key and value
        try:
            # Split on first '=' and strip whitespace
            if '=' not in meta_str:
                raise ValueError("Missing '=' in metadata")

            key, value_str = [part.strip() for part in meta_str.split('=', 1)]
            if not key:
                raise ValueError("Empty key in metadata")

            # Parse the value
            import ast
            try:
                # Try to parse as Python literal (for numbers, strings, lists, etc.)
                value = ast.literal_eval(value_str)
            except (ValueError, SyntaxError) as e:
                # All values must be valid Python literals
                raise ValueError(
                    f"Invalid value format: {value_str}. Must be a valid Python literal (use quotes for strings)") from e

            return cls(key=key, value=value)
        except Exception as e:
            raise ValueError(
                f"Invalid metadata format: {meta_str}. Expected 'key = value' where value is a valid Python literal") from e


class MessageNode(BaseModel):
    name: str
    content: str
    role: Optional[str] = None
    code_cell_id: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list] = None
    attributes: Optional[dict] = None
    code_cells: Optional[List[CodeCellNode]] = None
    meta: Optional[dict] = None

    @classmethod
    def create(cls, tokens: ParseResults):
        dct = tokens.as_dict()
        child_nodes = dct.pop("child_nodes")
        dct["meta"] = {}

        # First pass: collect metadata
        for node in child_nodes:
            if isinstance(node, MetaNode):
                dct["meta"][node.key] = node.value
            elif isinstance(node, MetaTagNode):
                # Handle HTML meta tags
                for key, value in node.attributes.items():
                    dct["meta"][key] = value

        # Second pass: build content
        filtered_content = []
        inside_special_block = False

        for node in child_nodes:
            if isinstance(node, (CodeCellNode, PreBlockNode)):
                inside_special_block = True
                if isinstance(node, PreBlockNode):
                    # Use unescaped content for PreBlockNode
                    filtered_content.append(node.unescaped)
                else:
                    filtered_content.append(node.source)
            elif isinstance(node, (CommentNode, MetaNode, MetaTagNode)) and not inside_special_block:
                # Skip comments and metadata outside special blocks
                continue
            elif isinstance(node, str):
                # Handle plain string nodes
                filtered_content.append(node)
                inside_special_block = False
            else:
                filtered_content.append(node.source)
                inside_special_block = False

        dct["content"] = "".join(filtered_content)
        dct["code_cells"] = [n for n in child_nodes if isinstance(n, CodeCellNode) and n.eval]
        if not dct["code_cells"]:
            del dct["code_cells"]
        if not dct["meta"]:
            del dct["meta"]
        return MessageNode(**dct)

    def as_dict(self):
        return self.model_dump(exclude_unset=True)


def comment_line_parser():
    return (
            pp.LineStart()
            + pp.Literal('[//]: #')
            + pp.restOfLine
            + pp.LineEnd()
    ).set_parse_action(CommentNode.from_tokens)


def meta_line_parser():
    # Match the content between 'meta:' and ')'
    meta_content = pp.Regex(r'[^)]+')('meta_str')

    # The full meta line pattern
    meta_line = (
            pp.LineStart()
            + pp.Literal('[//]: # (meta:')
            + meta_content
            + pp.Literal(')')
            + pp.LineEnd()
    ).set_parse_action(lambda s, l, t: MetaNode.from_tokens(t))

    return meta_line


def message_content_parser():
    # Comments and metadata (strict line patterns)
    comment = comment_line_parser().setName("comment_line")
    meta = meta_line_parser().setName("meta_line")
    html_meta = meta_tag_parser().setName("html_meta_tag")

    # Code cells and pre tags (specific start/end patterns)
    code_cell = code_cell_parser().setName("code_cell")
    pre_tag = pre_tag_parser().setName("pre_tag_with_content_parser")

    # Regular text content (catch-all) - OPTIMIZED with two-tier regex
    # Fast path: greedy match for common characters (letters, numbers, spaces, common punctuation)
    # Slow path: when hitting special characters, use negative lookahead to check for section markers
    # This optimization reduces backtracking for plain text (the most common case)
    text_content = (
        pp.Regex(
            fr"(?:[^`<#*\[]+|{NOT_BEGINNING_OF_SECTION_AHEAD}.)+",
            re.DOTALL | re.MULTILINE
        )
    ).setName("text_content").set_parse_action(TextContentNode.from_tokens)

    # Define a single line that can be either metadata, comment, or text
    # OPTIMIZATION: text_content moved FIRST to prioritize the common case (plain text)
    line = (text_content | html_meta | meta | comment)

    return pp.Group(
        (line | code_cell | pre_tag)[...]
    ).setName("message_content_alternatives_parser")("child_nodes")


def first_message_parser(implicit_role: str = "user"):
    message_content = message_content_parser()
    implicit_header = (pp.LineStart().setName("first_message_start") +
                       pp.Empty().setName("implicit_role").setParseAction(lambda: implicit_role)("name"))
    first_message = (
            (headers_parser() | implicit_header).setName("message_header_parser")
            + message_content
            + pp.Optional(tool_calls_parser())
    ).setName("first_message")
    return first_message.set_parse_action(MessageNode.create)


def message_parser():
    message_content = message_content_parser()

    message = (
            pp.LineStart()
            + headers_parser().setName("message_header_parser")
            + message_content
            + pp.Optional(tool_calls_parser())
    ).setName("message_parser")
    return message.set_parse_action(MessageNode.create)


def messages_parser(implicit_role: str = "user"):
    first_message, message = first_message_parser(implicit_role=implicit_role), message_parser()
    messages = (first_message + message[...]).setName("messages_sequence").set_results_name("messages")

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


def test_messages_parser_simple_metadata():
    input = textwrap.dedent('''\
        Hello
        
        [//]: # (meta:foo='bar')
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Hello\n\n",
            'meta': {'foo': 'bar'}
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_invalid_metadata():
    input = textwrap.dedent('''\
        Hello
        
        [//]: # (meta:foo=bar)
        ''')

    with pytest.raises(ValueError):
        messages_parser().parseString(input)


def test_messages_parser_with_mixed_metadata():
    input = textwrap.dedent('''\
        **user>** Here's a message with mixed metadata

        [//]: # (meta:temperature = 0.7)
        This is some content.
        [//]: # (meta:top_p = 0.9)
        More content.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Here's a message with mixed metadata\n\nThis is some content.\nMore content.\n",
            'meta': {'temperature': 0.7, 'top_p': 0.9}
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_complex_metadata():
    input = textwrap.dedent('''\
        Hello
        
        [//]: # (meta:model = "gpt-4")
        [//]: # (meta:temperature = 0.7)
        [//]: # (meta:max_tokens = 100)
        [//]: # (meta:stop = ["END"])
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Hello\n\n",
            'meta': {
                'model': 'gpt-4',
                'temperature': 0.7,
                'max_tokens': 100,
                'stop': ['END']
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_html_entities_in_pre_tag():
    # Test with a simpler case that the parser can handle correctly
    input = textwrap.dedent('''\
        **user>** Test

        <pre>
        if x &gt; 5:
            print("x is greater")
        if y &lt; 10:
            print("y is less")
        &amp;&amp; means AND
        </pre>
        ''')

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    # Get the content of the first (and only) message
    content = parsed_messages[0]['content']

    # Verify that HTML entities inside <pre> tags are unescaped
    assert 'if x > 5:' in content  # &gt; should be unescaped to >
    assert 'if y < 10:' in content  # &lt; should be unescaped to <
    assert '&& means AND' in content  # &amp;&amp; should be unescaped to &&

    # Verify that the escaped versions are NOT present in the content
    # Note: They might still appear in the header, but not inside the pre tag content
    pre_start = content.find('<pre>')
    pre_end = content.find('</pre>')
    pre_content = content[pre_start:pre_end + 6]  # Include the closing tag

    assert '&gt;' not in pre_content
    assert '&lt;' not in pre_content
    assert '&amp;&amp;' not in pre_content


def test_messages_parser_with_pre_tag_between_messages():
    """Test that messages are correctly split when there's a pre tag between them."""
    input = textwrap.dedent('''\
        **user>** First message with pre tag:
        
        <pre>
        Some content
        </pre>
        
        **assistant>** Second message.
        ''')

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    # Should have 2 messages
    assert len(parsed_messages) == 2
    assert parsed_messages[0]['name'] == 'user'
    assert parsed_messages[1]['name'] == 'assistant'
    assert parsed_messages[1]['content'] == 'Second message.\n'


def test_messages_parser_with_closing_pre_tag_before_header():
    """Test message splitting with closing pre tag immediately before a header."""
    input = textwrap.dedent('''\
        **user>** Message with pre:
        <pre>
        Content
        </pre>
        **assistant>** Next message.
        ''')

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    # Should have 2 messages
    assert len(parsed_messages) == 2
    assert parsed_messages[0]['name'] == 'user'
    assert parsed_messages[1]['name'] == 'assistant'


def test_messages_parser_with_html_meta_tags():
    input = textwrap.dedent('''\
        **user>** Message with HTML meta tags
        
        <meta name="foo" content="bar" />
        <meta name="author" content="John Doe" />
        
        Some content after meta tags.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Message with HTML meta tags\n\n\nSome content after meta tags.\n",  # Extra newline from blank line between meta tags
            'meta': {
                'foo': 'bar',
                'author': 'John Doe'
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_with_mixed_meta_formats():
    input = textwrap.dedent('''\
        **user>** Message with mixed metadata formats
        
        <meta name="description" content="A test message" />
        [//]: # (meta:temperature = 0.7)
        <meta charset="UTF-8" />
        
        Content here.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': "Message with mixed metadata formats\n\n\nContent here.\n",  # Extra newline from blank line between metadata
            'meta': {
                'description': 'A test message',  # Transformed from name/content
                'temperature': 0.7,
                'charset': 'UTF-8'
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_html_meta_in_code_block():
    input = textwrap.dedent('''\
        **user>** Meta tag in code block should be preserved
        
        ```html
        <meta name="viewport" content="width=device-width" />
        ```
        
        <meta name="real" content="metadata" />
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': 'Meta tag in code block should be preserved\n\n```html\n<meta name="viewport" content="width=device-width" />\n```\n\n',
            'meta': {
                'real': 'metadata'  # Transformed from name/content
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_html_meta_in_pre_tag():
    input = textwrap.dedent('''\
        **user>** Meta tag in pre block should be preserved
        
        <pre>
        <meta name="inside-pre" content="should be preserved" />
        </pre>
        
        <meta name="outside" content="should be parsed" />
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': 'Meta tag in pre block should be preserved\n\n<pre>\n<meta name="inside-pre" content="should be preserved" />\n</pre>\n\n',
            'meta': {
                'outside': 'should be parsed'  # Transformed from name/content
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages


def test_messages_parser_multiple_messages_with_html_meta():
    input = textwrap.dedent('''\
        **user>** First message
        
        <meta name="user-meta" content="user value" />
        
        **assistant>** Second message
        
        <meta name="assistant-meta" content="assistant value" />
        
        Done.
        ''')

    expected_messages = [
        {
            'name': 'user',
            'content': 'First message\n\n\n',  # Extra newline from blank line after meta tag
            'meta': {
                'user-meta': 'user value'  # Transformed from name/content
            }
        },
        {
            'name': 'assistant',
            'content': 'Second message\n\n\nDone.\n',  # Extra newline from blank line after meta tag
            'meta': {
                'assistant-meta': 'assistant value'  # Transformed from name/content
            }
        }
    ]

    results = messages_parser().parseString(input)
    parsed_messages = [m.as_dict() for m in results.messages]

    assert parsed_messages == expected_messages
