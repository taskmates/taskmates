from taskmates.workflows.contexts.context import Context
from taskmates.workflow_engine.run import Run


# TODO: Remove this class
class EditorAppender:
    def __init__(self, project_dir: str, chat_file: str, run: Run[Context]):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.run = run

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.run.signals["output_streams"].response.send_async(sanitized)

