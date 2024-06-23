import json

import pyparsing as pp


def chat_message_header_parser():
    name = pp.Word(pp.printables, excludeChars=" {*")("name")

    json_str = (pp.QuotedString('{', endQuoteChar='}', escChar='\\', unquoteResults=False)
                .setParseAction(lambda t: json.loads(t[0]))("attributes"))
    attributes = (pp.Optional(pp.Suppress(" ") + json_str))

    chat_message_header = (
            pp.LineStart()
            + pp.Suppress("**") + name + attributes + pp.Suppress("**")
            + pp.Suppress(pp.Literal(" ") | pp.Literal("\n")))
    return chat_message_header


def test_message_header_parser_without_attributes():
    input = "**user** message content"
    result = chat_message_header_parser().parseString(input)
    assert result.name == "user"


def test_message_header_parser_with_attributes():
    input = "**user {\"name\": \"john\", \"age\": 30}** message content"
    result = chat_message_header_parser().parseString(input)
    assert result.name == "user"
    assert result.attributes == {"name": "john", "age": 30}
