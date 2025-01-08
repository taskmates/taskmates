import pyparsing as pp


def pre_tag_parser():
    pre_tag = pp.Combine(
        (pp.LineStart() + pp.Literal("<pre")
         - pp.SkipTo((pp.Literal("</pre>") + pp.Optional(pp.LineEnd())) | pp.StringEnd(), include=True))
    )
    return pre_tag
