from taskmates.core.markdown_chat.grammar.parsers.message.header.chat_message_header_parser import chat_message_header_parser
from taskmates.core.markdown_chat.grammar.parsers.message.header.code_cell_execution_header_parser import code_cell_execution_header_parser
from taskmates.core.markdown_chat.grammar.parsers.message.header.tool_execution_header_parser import tool_execution_header_parser


def headers_parser():
    message_header = chat_message_header_parser()
    tool_execution_header = tool_execution_header_parser()
    code_cell_execution_header = code_cell_execution_header_parser()
    return (
            message_header
            | tool_execution_header
            | code_cell_execution_header
    )
