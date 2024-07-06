import re

import pyparsing as pp


def code_cell_parser():
    code_cell_start = (pp.line_start + pp.Regex(r"```[a-z]*( \.eval)?", re.MULTILINE) + pp.line_end).set_name(
        "code_cell_start")
    code_cell_end = pp.Regex(r"^```\n", re.MULTILINE).set_name("code_cell_end")

    code_cell = pp.Forward().set_name("code_cell")
    code_cell <<= pp.Combine(
        code_cell_start +
        pp.OneOrMore(
            pp.Combine(pp.line_start + ~code_cell_end + pp.SkipTo(pp.line_end, include=True) | code_cell).set_name(
                "code_cell_line")
        ) +
        code_cell_end
    )
    return code_cell
