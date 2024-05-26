from taskmates.assistances.code_execution.jupyter_.code_execution import CodeExecution
from taskmates.assistances.markdown.editor_appender import EditorAppender


class ToolEditorCompletion:
    def __init__(self, project_dir: str, chat_file: str):
        self.editor_appender = EditorAppender(project_dir, chat_file)

    async def append(self, text: str, signals):
        await self.editor_appender.append(text, signals)

    async def append_tool_execution_footer(self, function_title: str, signals):
        await self.append(CodeExecution.format_tool_output_footer(function_title), signals)

    async def append_tool_execution_header(self, function_title: str, tool_call_id: str, signals):
        await self.append(CodeExecution.format_tool_output_header(function_title, tool_call_id), signals)
