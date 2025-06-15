from typeguard import typechecked

from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals


# TODO: Remove this class
@typechecked
class EditorAppender:
    def __init__(
            self,
            project_dir: str,
            chat_file: str,
            markdown_completion_signals: MarkdownCompletionSignals):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.markdown_completion_signals = markdown_completion_signals

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.markdown_completion_signals.response.send_async(sanitized)
