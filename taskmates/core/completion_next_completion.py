from taskmates.contexts import Contexts
from taskmates.core.chat_completion.chat_completion_provider import ChatCompletionProvider
from taskmates.core.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.code_execution.tools.tool_execution_completion_provider import ToolExecutionCompletionProvider
from taskmates.signals.signals import Signals


def compute_next_step(chat, contexts: Contexts, signals: Signals):
    assistances = [
        CodeCellExecutionCompletionProvider(contexts, signals),
        ToolExecutionCompletionProvider(contexts, signals),
        ChatCompletionProvider(contexts, signals)
    ]

    for assistance in assistances:
        if assistance.can_complete(chat):
            return assistance

    return None
