from loguru import logger

from taskmates.core.actions.chat_completion.chat_completion_provider import ChatCompletionProvider
from taskmates.core.actions.code_execution.code_cells.code_cell_execution_completion_provider import \
    CodeCellExecutionCompletionProvider
from taskmates.core.actions.code_execution.tools.tool_execution_completion_provider import \
    ToolExecutionCompletionProvider


def compute_next_completion(chat):
    logger.debug(f"Computing next completion")

    assistances = [
        # TODO: all of these must emit some common interface  "markdown_completion"
        CodeCellExecutionCompletionProvider(),
        ToolExecutionCompletionProvider(),
        ChatCompletionProvider()
    ]

    for assistance in assistances:
        if assistance.can_complete(chat):
            logger.debug(f"Next completion: {assistance}")

            return assistance

    return None
