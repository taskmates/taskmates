from dataclasses import dataclass
import html

import pyparsing as pp


@dataclass
class PreBlockNode:
    source: str
    unescaped: str

    @classmethod
    def from_tokens(cls, tokens):
        source = tokens[0]
        unescaped = html.unescape(source)
        return cls(source=source, unescaped=unescaped)


def pre_tag_parser():
    pre_tag = pp.Combine(
        (pp.LineStart() + pp.Literal("<pre")
         - pp.SkipTo((pp.Literal("</pre>") + pp.Optional(pp.LineEnd())) | pp.StringEnd(), include=True))
    ).set_parse_action(PreBlockNode.from_tokens)
    return pre_tag


def test_basic_pre_tag():
    input = "<pre>Hello World</pre>\n"
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input


def test_pre_tag_with_multiple_lines():
    input = """<pre>
Line 1
Line 2
Line 3
</pre>
"""
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input


def test_pre_tag_without_closing_tag():
    input = "<pre>Unclosed content"
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input


def test_pre_tag_with_special_characters():
    input = """<pre>
Special chars: & < > " ' $ # @ ! % ^ * ( ) + = { } [ ] | \\ / ? , . ; :
</pre>
"""
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input


def test_pre_tag_empty():
    input = "<pre></pre>\n"
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input


def test_pre_tag_with_html_content():
    input = """<pre>&lt;div&gt;Hello World&lt;/div&gt;</pre>
"""
    expected_unescaped = """<pre><div>Hello World</div></pre>
"""
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == expected_unescaped
