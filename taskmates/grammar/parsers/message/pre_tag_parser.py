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
    # Define start and end tags more precisely
    pre_start = pp.LineStart() + pp.Literal("<pre") + pp.Optional(pp.SkipTo(">")) + ">"
    pre_end = "</pre>" + pp.LineEnd()
    
    # Define content more explicitly
    content_char = ~pp.Literal("</pre>") + pp.Word(pp.printables + ' \t') | pp.LineEnd()
    pre_content = pp.ZeroOrMore(content_char)
    
    # Combine all parts
    pre_tag = pp.Combine(
        pre_start +
        pre_content +
        (pre_end | pp.StringEnd())
    ).setName("pre_tag_block").set_parse_action(PreBlockNode.from_tokens)
    
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
    input = """<pre><div>Hello World</div></pre>
"""
    expected_unescaped = """<pre><div>Hello World</div></pre>
"""
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == expected_unescaped


def test_pre_tag_with_attributes():
    input = """<pre class='output' style='display:none'>
Some content
</pre>
"""
    result = pre_tag_parser().parseString(input)[0]
    assert result.source == input
    assert result.unescaped == input
