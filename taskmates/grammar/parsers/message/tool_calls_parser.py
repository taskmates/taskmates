import json
import re
import textwrap

import pyparsing as pp

from taskmates.grammar.parsers.snake_case import snake_case

TOOL_CALLS_START_REGEX = r"^###### Steps"


def parse_tool_call(string, location, tokens):
    tool_call = tokens[0]
    tool_call_name = tool_call['name']

    # pyparsing bug https://stackoverflow.com/a/23332407/1553243
    arguments = tool_call['arguments'].replace("\n", "\\n")

    return {
        "id": tool_call['id'],
        "type": "function",
        "function": {
            "name": snake_case(tool_call_name),
            "arguments": json.loads(arguments)
        }
    }


def tool_call_parser():
    tool_name = pp.Word(pp.alphas + " ")("name")
    tool_id = pp.Suppress("[") + pp.Word(pp.nums)("id") + pp.Suppress("]")
    tool_args = pp.QuotedString(quoteChar="`", unquoteResults=True, escChar=None)("arguments")

    tool_call = pp.Group(
        pp.Suppress("-") +
        tool_name +
        tool_id +
        pp.Suppress(" ") +
        tool_args
    ).setParseAction(parse_tool_call)

    return tool_call


def tool_calls_parser():
    section_header = pp.Regex(TOOL_CALLS_START_REGEX, re.MULTILINE).suppress()
    tool_call = tool_call_parser()

    return pp.Group(section_header
                    + pp.OneOrMore(pp.LineEnd()).suppress()
                    + pp.OneOrMore(tool_call
                                   + pp.Optional(pp.LineEnd()).suppress())
                    + pp.ZeroOrMore(pp.LineEnd().suppress())
                    )("tool_calls")


def test_tool_calls_parser():
    matching_content = textwrap.dedent("""\
        ###### Steps
        - Run Shell Command [1] `{"cmd":"cd /tmp\\npwd"}`
        
        """)

    extra_content = textwrap.dedent("""\
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        **user>** Here is another message.
        
        """)

    input = matching_content + extra_content

    expected_result = [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "arguments": {
                    "cmd": "cd /tmp\npwd"
                }
            }
        }
    ]

    extra_content = pp.SkipTo(pp.StringEnd(), include=True)("extra_content")
    results = (tool_calls_parser() + extra_content).parseString(input)

    matched_text = "".join(pp.original_text_for(
        tool_calls_parser(),
    ).parseString(input))

    assert matched_text == matching_content

    assert results.tool_calls.as_list() == expected_result
    assert results.remaining_text == extra_content
