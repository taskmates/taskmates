import textwrap

import pyparsing as pp
import yaml


def remaining_content_parser():
    return pp.SkipTo(pp.string_end)("remaining_content")


def front_matter_parser():
    def convert_to_yaml(s, l, t):
        return yaml.safe_load(t[0])

    front_matter = (pp.QuotedString('---\n', multiline=True, unquoteResults=True)
                    .set_parse_action(convert_to_yaml)
                    .set_results_name("front_matter") + pp.ZeroOrMore(pp.Suppress(pp.Literal("\n"))))
    return front_matter


def test_front_matter_parser():
    input = textwrap.dedent("""\
        ---
        key1: value1
        key2:
          - item1
          - item2
        ---
        
        **user** Message
        """)
    result = (front_matter_parser() + remaining_content_parser()).parse_string(input)
    assert result.front_matter == {'key1': 'value1', 'key2': ['item1', 'item2']}
    assert result.remaining_content == textwrap.dedent("""\
        **user** Message
    """)
