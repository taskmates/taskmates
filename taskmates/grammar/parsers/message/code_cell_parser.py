import re
import textwrap

import pyparsing as pp


def code_cell_parser():
    code_cell_with_language_start = pp.Combine(
        pp.line_start + pp.Regex(r"```[a-zA-Z0-9]+( \.eval)?", re.MULTILINE) + pp.line_end).set_name(
        "code_cell_with_language_start")
    code_cell_with_language = pp.Forward().set_name("code_cell_with_language")
    code_cell_end = pp.Regex(r"^```(`*)(\n|\Z)", re.MULTILINE).set_name("code_cell_end")

    code_cell_with_language <<= pp.Combine(
        code_cell_with_language_start -
        pp.OneOrMore(
            pp.Combine(
                pp.line_start + ~code_cell_end
                - (code_cell_with_language | pp.SkipTo(pp.line_end, include=True)))

        ).set_name("code_cell_content") -
        (code_cell_end | pp.StringEnd())
    )

    code_cell_without_language = pp.Forward().set_name("code_cell_without_language")
    code_cell_without_language_start = pp.Regex(r"^```(`*)(\n|\Z)", re.MULTILINE).set_name(
        "code_cell_without_language_start")

    code_cell_without_language <<= pp.Combine(
        code_cell_without_language_start +
        pp.OneOrMore(
            pp.Combine(
                pp.line_start + ~code_cell_end - pp.SkipTo(
                    pp.line_end,
                    include=True))
        ) -
        (code_cell_end | pp.StringEnd())
    )

    return code_cell_with_language | code_cell_without_language


def test_code_cell_with_language():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello, World!")
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


def test_code_cell_with_language_and_eval():
    input = textwrap.dedent("""\
        ```python .eval
        print("Hello, World!")
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


def test_code_cell_without_language():
    input = textwrap.dedent("""\
        ```
        Some text without language specification
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


def test_nested_code_cells():
    input = textwrap.dedent("""\
        ```markdown
        Here's a code block:
        ```python
        print("hello")
        ```
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


def test_code_cell_with_multiple_lines():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello")
            
        def world():
            print("World")
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


def test_code_cell_with_no_closing_backticks():
    input = textwrap.dedent("""\
        ```python
        def hello():
            print("Hello")
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input


# TODO unsupported
# def test_code_cell_with_hyphenated_language():
#     input = textwrap.dedent("""\
#         ```shell-script
#         echo "Hello"
#         ```
#         """)
#
#     result = code_cell_parser().parseString(input)[0]
#     assert result == input


def test_code_cell_with_numbers_in_language():
    input = textwrap.dedent("""\
        ```python3
        print("Hello")
        ```
        """)

    result = code_cell_parser().parseString(input)[0]
    assert result == input
