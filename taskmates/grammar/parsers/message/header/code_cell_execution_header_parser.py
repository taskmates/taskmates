import re
import textwrap

import pyparsing as pp


def code_cell_execution_header_parser():
    execution_header = pp.Regex("^###### Cell Output: ", re.MULTILINE).suppress()

    code_cell_name = pp.Word(pp.alphas)("name")
    code_cell_role = pp.Empty().setParseAction(lambda: "cell_output")("role")

    # noinspection PyTypeChecker
    code_cell_id = (pp.Suppress("[")
                    - pp.Regex(f"[{pp.identchars}][{pp.identbodychars}]*")("code_cell_id")
                    - pp.Suppress("]"))
    code_cell_execution_header = (
            execution_header -
            code_cell_name -
            pp.Literal(" ").suppress() -
            code_cell_id -
            pp.LineEnd() -
            code_cell_role
    )
    return code_cell_execution_header


def test_code_cell_execution_parser():
    input = textwrap.dedent("""\
        ###### Cell Output: stdout [cell_0]
        
        <pre>
        OUTPUT 1
        </pre>
        
        """)
    expected_result = {
        'role': 'cell_output',
        'name': 'stdout',
        'code_cell_id': 'cell_0',
    }

    results = code_cell_execution_header_parser().parseString(input)

    assert results.as_dict() == expected_result
