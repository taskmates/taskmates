import logging


class EditorAppender:
    def __init__(self, project_dir: str, chat_file: str):
        self.appended_completions = []
        self.chat_file = chat_file
        self.project_dir = project_dir
        self.logger = logging.getLogger(__name__)

    async def append(self, text: str, signals):
        sanitized = text.replace("\r", "")
        if not sanitized:
            return

        self.appended_completions.append(sanitized)

        try:
            await signals.response.send_async(sanitized)
        except Exception as e:
            self.logger.exception(f"Failed to send completion chunk: {e}")
            self.logger.error(f"Text: \n{text}")

    def get_appended_completions(self) -> str:
        return "".join(self.appended_completions)
