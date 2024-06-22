import json

import pyparsing as pp


def chat_message_header_parser():
    header_delimiter = pp.Suppress("**").leave_whitespace()

    name = pp.Word(pp.printables, excludeChars=" {*")

    json_str = pp.QuotedString('{', endQuoteChar='}', escChar='\\', unquoteResults=False)
    attributes = (pp.Optional(pp.Suppress(" ") + json_str)
                  .setParseAction(lambda t: json.loads(t[0]) if t else {})).leave_whitespace()

    chat_message_header = ( header_delimiter + name("name") + attributes("attributes") + header_delimiter + pp.Suppress(
        pp.Literal(" ") | pp.Literal("\n")).leave_whitespace())
    return chat_message_header


def test_message_header_parser_without_attributes():
    input = "**user** message content"
    result = chat_message_header_parser().parseString(input)
    assert result.name == "user"
    assert result.attributes == {}


def test_message_header_parser_with_attributes():
    input = "**user {\"name\": \"john\", \"age\": 30}** message content"
    result = chat_message_header_parser().parseString(input)
    assert result.name == "user"
    assert result.attributes == {"name": "john", "age": 30}
