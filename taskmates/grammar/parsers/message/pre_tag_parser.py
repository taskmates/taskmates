import pyparsing as pp


def pre_tag_parser():
    pre_tag = pp.Combine(
        (pp.LineStart() + pp.Literal("<pre")
         - pp.SkipTo(pp.LineStart() + pp.Literal("</pre>") + pp.LineEnd(), include=True))
    )
    return pre_tag
