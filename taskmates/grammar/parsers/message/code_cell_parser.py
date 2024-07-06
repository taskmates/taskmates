import pyparsing as pp


def code_cell_parser():
    code_cell_delimiter = pp.LineStart() + pp.Literal("```")
    code_cell = pp.Combine(
        (code_cell_delimiter
         - pp.SkipTo(code_cell_delimiter + pp.LineEnd(), include=True))
    )
    return code_cell
