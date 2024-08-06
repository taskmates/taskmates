import re

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
        code_cell_end
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
        code_cell_end
    )

    return code_cell_with_language | code_cell_without_language
