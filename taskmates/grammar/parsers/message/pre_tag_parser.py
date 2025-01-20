from dataclasses import dataclass

import pyparsing as pp


@dataclass
class PreBlockNode:
    source: str

    @classmethod
    def from_tokens(cls, tokens):
        return cls(source=tokens[0])


def pre_tag_parser():
    pre_tag = pp.Combine(
        (pp.LineStart() + pp.Literal("<pre")
         - pp.SkipTo((pp.Literal("</pre>") + pp.Optional(pp.LineEnd())) | pp.StringEnd(), include=True))
    ).set_parse_action(PreBlockNode.from_tokens)
    return pre_tag
