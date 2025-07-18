from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.code_execution import CodeExecution
from taskmates.core.workflows.markdown_completion.completions.tool_execution.editor_appender import EditorAppender
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals


class ToolExecutionAppender:
    def __init__(self, project_dir: str, chat_file: str, markdown_completion_signals: MarkdownCompletionSignals):
        self.editor_appender = EditorAppender(project_dir, chat_file, markdown_completion_signals)

    async def append(self, text: str):
        await self.editor_appender.append(text)

    async def append_tool_execution_footer(self, function_title: str):
        await self.append(CodeExecution.format_tool_output_footer(function_title))

    async def append_tool_execution_header(self, function_title: str, tool_call_id: str):
        await self.append(CodeExecution.format_tool_output_header(function_title, tool_call_id))
