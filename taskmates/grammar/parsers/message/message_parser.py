import pyparsing as pp

from taskmates.grammar.parsers.message.header.chat_message_header_parser import chat_message_header_parser
from taskmates.grammar.parsers.message.header.code_cell_execution_header_parser import code_cell_execution_header_parser
from taskmates.grammar.parsers.message.header.tool_execution_header_parser import tool_execution_header_parser
from taskmates.grammar.parsers.message.tool_calls_parser import tool_calls_parser

message_entry = pp.Forward()

message_header = chat_message_header_parser()
tool_execution_header = tool_execution_header_parser()
code_cell_execution_header = code_cell_execution_header_parser()
message_tool_calls = tool_calls_parser()
headers = (message_header | tool_execution_header | code_cell_execution_header)

message_content = pp.SkipTo(message_tool_calls | message_entry | pp.stringEnd, include=False).leave_whitespace()(
    "content")

message_entry <<= pp.Group(
    headers
    + message_content
    + pp.Optional(message_tool_calls))


def first_message_parser():
    global message_entry

    message_content = pp.SkipTo(message_tool_calls | message_entry | pp.stringEnd, include=False).leave_whitespace()(
        "content")
    implicit_message_header = (pp.line_start
                               + pp.Empty().setParseAction(lambda: "user")("name")
                               )
    headers = (message_header | tool_execution_header | code_cell_execution_header | implicit_message_header)

    first_message = pp.Group(
        headers
        + message_content
        + pp.Optional(message_tool_calls))

    return first_message


def message_parser():
    global message_entry

    return message_entry
