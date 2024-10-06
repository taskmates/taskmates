from taskmates.core.execution_context import ExecutionContext


# TODO: Remove this class
class EditorAppender:
    def __init__(self, project_dir: str, chat_file: str, execution_context: ExecutionContext):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.execution_context = execution_context

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.execution_context.output_streams.response.send_async(sanitized)

