from taskmates.core.actions.code_execution.code_cells.code_execution import CodeExecution
from taskmates.core.actions.code_execution.tools.editor_appender import EditorAppender
from taskmates.core.signals.signals_context import SignalsContext


class ToolEditorCompletion:
    def __init__(self, project_dir: str, chat_file: str, signals: SignalsContext):
        self.editor_appender = EditorAppender(project_dir, chat_file, signals)

    async def append(self, text: str):
        await self.editor_appender.append(text)

    async def append_tool_execution_footer(self, function_title: str):
        await self.append(CodeExecution.format_tool_output_footer(function_title))

    async def append_tool_execution_header(self, function_title: str, tool_call_id: str):
        await self.append(CodeExecution.format_tool_output_header(function_title, tool_call_id))
