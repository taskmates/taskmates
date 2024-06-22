import textwrap

import pyparsing as pp


def code_cell_execution_header_parser():
    execution_header = pp.Suppress(pp.line_start + pp.Literal("###### Cell Output: "))

    def code_cell_name(s, loc, toks):
        return "cell_output"
        # TODO: this conflicts with data/images
        # return "cell_output_" + toks[0]

    code_cell_name = pp.Word(pp.alphas).set_parse_action(code_cell_name).leave_whitespace()("name")
    # noinspection PyTypeChecker
    code_cell_id = pp.Suppress("[") + pp.Combine(pp.Word(pp.identchars) + pp.Word(pp.identbodychars))(
        "code_cell_id") + pp.Suppress("]")
    code_cell_execution_header = (
                execution_header + code_cell_name + pp.Literal(" ").suppress() + code_cell_id + pp.LineEnd())
    return code_cell_execution_header.leave_whitespace()


def test_code_cell_execution_parser():
    input = textwrap.dedent("""\
        ###### Cell Output: stdout [cell_0]
        
        <pre>
        OUTPUT 1
        </pre>
        
        """)
    expected_result = {
        'name': 'cell_output',
        'code_cell_id': 'cell_0',
    }

    results = code_cell_execution_header_parser().parseString(input)

    assert results.as_dict() == expected_result
