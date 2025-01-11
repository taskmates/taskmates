import re

import pyparsing as pp


def code_cell_parser():
    code_cell_with_language_start = pp.Combine(
        pp.line_start + pp.Regex(r"```[a-zA-Z0-9]+( \.eval)?", re.MULTILINE) + pp.line_end).set_name(
        "code_cell_with_language_start")
    code_cell_with_language = pp.Forward().set_name("code_cell_with_language")
    code_cell_end = pp.Regex(r"^```(`*)(\n|\Z)", re.MULTILINE).set_name("code_cell_end")

    def set_partial(tokens):
        tokens["partial"] = True
        return tokens

    code_cell_content = pp.OneOrMore(
        pp.Combine(
            pp.line_start + ~code_cell_end
            - (code_cell_with_language | pp.SkipTo(pp.line_end, include=True)))
    ).set_name("code_cell_content")

    code_cell_with_language <<= pp.Group(
        pp.Combine(
            code_cell_with_language_start +
            code_cell_content +
            (code_cell_end | pp.StringEnd())
        )
    ).set_parse_action(lambda t: set_partial(t[0]) if t[0][-1] == "\n" else t[0])

    code_cell_without_language = pp.Forward().set_name("code_cell_without_language")
    code_cell_without_language_start = pp.Regex(r"^```(`*)(\n|\Z)", re.MULTILINE).set_name(
        "code_cell_without_language_start")

    code_cell_without_language <<= pp.Group(
        pp.Combine(
            code_cell_without_language_start +
            code_cell_content +
            (code_cell_end | pp.StringEnd())
        )
    ).set_parse_action(lambda t: set_partial(t[0]) if t[0][-1] == "\n" else t[0])

    return code_cell_with_language | code_cell_without_language
