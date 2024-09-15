from taskmates.core.signals.signals_context import SignalsContext


# TODO: Remove this class
class EditorAppender:
    def __init__(self, project_dir: str, chat_file: str, signals: SignalsContext):
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.signals = signals

    async def append(self, text: str):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        await self.signals.response.response.send_async(sanitized)

