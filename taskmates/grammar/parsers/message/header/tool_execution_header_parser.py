import textwrap

import pyparsing as pp

from taskmates.grammar.parsers.snake_case_action import snake_case_action


def tool_execution_header_parser():
    execution_header = pp.Suppress(pp.Literal("###### Execution:"))
    role = pp.Empty().set_parse_action(pp.replace_with("tool"))("role")
    tool_name = pp.Word(pp.alphas + " ").set_parse_action(snake_case_action)("name")
    tool_id = pp.Suppress("[") + pp.Word(pp.nums)("tool_call_id") + pp.Suppress("]")
    tool_execution_header = (role + execution_header + tool_name + tool_id + pp.LineEnd())
    return tool_execution_header.leave_whitespace()


def test_tool_execution_parser():
    input = textwrap.dedent("""\
        ###### Execution: Run Shell Command [1]
        
        <pre>
        OUTPUT 1
        </pre>
        
        """)
    expected_result = {
        'role': 'tool',
        'name': 'run_shell_command',
        'tool_call_id': '1',
    }

    results = tool_execution_header_parser().parseString(input)

    assert results.as_dict() == expected_result
