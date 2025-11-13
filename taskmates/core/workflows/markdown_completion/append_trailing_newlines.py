from taskmates.core.chat.openai.get_text_content import get_text_content
from taskmates.core.markdown_chat.compute_trailing_newlines import compute_trailing_newlines
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals


async def append_trailing_newlines(message: dict,
                                   execution_environment: ExecutionEnvironmentSignals):
    if has_truncated_code_cell(message):
        return

    content = get_text_content(message)

    newlines = compute_trailing_newlines(content)
    if newlines:
        await execution_environment.response.send_async(sender="formatting", value=newlines)
