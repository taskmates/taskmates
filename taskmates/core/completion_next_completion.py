from taskmates.core.chat_completion.chat_completion_provider import ChatCompletionProvider
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider


def compute_next_completion(chat):
    assistances = [
        CodeCellExecutionCompletionProvider(),
        ToolExecutionCompletionProvider(),
        ChatCompletionProvider()
    ]

    for assistance in assistances:
        if assistance.can_complete(chat):
            return assistance

    return None
