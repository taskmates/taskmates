from taskmates.workflow_engine.environment_signals import EnvironmentSignals


# TODO: Remove this class
class EditorAppender:
    def __init__(self, project_dir: str, chat_file: str, completion_signals: EnvironmentSignals):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.completion_signals = completion_signals

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.completion_signals["output_streams"].response.send_async(sanitized)
