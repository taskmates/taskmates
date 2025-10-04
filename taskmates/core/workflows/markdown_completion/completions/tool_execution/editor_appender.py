from typeguard import typechecked

from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals


# TODO: Remove this class
@typechecked
class EditorAppender:
    def __init__(
            self,
            project_dir: str,
            chat_file: str,
            execution_environment_signals: ExecutionEnvironmentSignals):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.execution_environment_signals = execution_environment_signals

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.execution_environment_signals.response.send_async(sender="response", value=sanitized)
