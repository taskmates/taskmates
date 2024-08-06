from taskmates.core.chat_completion.chat_completion_provider import ChatCompletionProvider
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.config.completion_opts import CompletionOpts


def compute_next_completion(chat, completion_opts: CompletionOpts):
    assistances = [
        CodeCellExecutionCompletionProvider(),
        ToolExecutionCompletionProvider(),
        ChatCompletionProvider(completion_opts)
    ]

    for assistance in assistances:
        if assistance.can_complete(chat):
            return assistance

    return None
