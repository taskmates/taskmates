import re
import textwrap
from typing import Optional

import pyparsing as pp
from pydantic import BaseModel


class CodeCellNode(BaseModel):
    source: str
    content: str
    language: Optional[str] = None
    eval: Optional[bool] = None
    truncated: Optional[bool] = None

    @classmethod
    def from_tokens(cls, tokens):
        group = tokens[0]
        if len(group) == 3:
            header, content, end = group
            header_dct = header.as_dict()
        else:
            header, content = group
            header_dct = header.as_dict()
            header_dct["truncated"] = True

        if "eval" in header_dct:
            header_dct["eval"] = True

        source = ""

        for s in tokens.as_list(flatten=True):
            if isinstance(s, str):
                source += s
            if isinstance(s, CodeCellNode):
                source += s.source

        attrs = {
            "source": source,
            "content": content,
            **header_dct
        }
        return cls(**attrs)

    def __str__(self):
        return self.source

    def as_dict(self):
        return self.model_dump(exclude_unset=True)


def code_cell_parser():
    code_cell_start = pp.Group(
        pp.line_start
        + pp.Regex(r"```")
        + pp.Optional(pp.Regex(r"[a-zA-Z0-9]+", re.MULTILINE))("language")
        + pp.Optional(" ")
        + pp.Optional(pp.Literal(".eval"))("eval")
        + pp.line_end
    )

    code_cell = pp.Forward()
    code_cell_end = pp.Regex(r"^```(`*)(\n|\Z)", re.MULTILINE)("end")

    code_cell_content = pp.Combine(pp.OneOrMore(
        pp.Combine(
            pp.line_start + ~code_cell_end
            - (code_cell | pp.SkipTo(pp.line_end, include=True))
        )
    ))("content")

    code_cell <<= pp.Group(
        code_cell_start
        - code_cell_content
        - (code_cell_end | pp.StringEnd())
    ).set_parse_action(CodeCellNode.from_tokens)

    return code_cell


def test_code_cell_with_language():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello, World!")
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'language': 'python',
        'content': 'def hello():\n    print("Hello, World!")\n'
    }


def test_code_cell_with_language_and_eval():
    input = textwrap.dedent("""\
        ```python .eval
        print("Hello, World!")
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'content': 'print("Hello, World!")\n',
        'language': 'python',
        'eval': True
    }


def test_code_cell_without_language():
    input = textwrap.dedent("""\
        ```
        Some text without language specification
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'content': 'Some text without language specification\n',
    }


def test_nested_code_cells():
    input = textwrap.dedent("""\
        ```markdown
        Here's a code block:
        ```python
        print("hello")
        ```
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'content': 'Here\'s a code block:\n```python\nprint("hello")\n```\n',
        'language': 'markdown',
    }


def test_code_cell_with_multiple_lines():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello")
            
        def world():
            print("World")
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'language': 'python',
        'content': 'def hello():\n'
                   '    print("Hello")\n'
                   '\n'
                   'def world():\n'
                   '    print("World")\n',
    }


def test_code_cell_with_no_closing_backticks():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello")
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'language': 'python',
        'content': 'def hello():\n    print("Hello")\n',
        'truncated': True
    }


def test_code_cell_with_numbers_in_language():
    input = textwrap.dedent("""\
        ```python3
        print("Hello")
        ```
        """)

    result = code_cell_parser().parseString(input)[0].as_dict()
    assert result == {
        "source": input,
        'language': 'python3',
        'content': 'print("Hello")\n',
    }

# TODO unsupported
# def test_code_cell_with_hyphenated_language():
#     input = textwrap.dedent("""\
#         ```shell-script
#         echo "Hello"
#         ```
#         """)
#
#     result = code_cell_parser().parseString(input)[0].as_dict()
#     assert result == { "source": input }
