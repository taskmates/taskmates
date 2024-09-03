from taskmates.core.compute_separator import compute_separator
from taskmates.core.signals import SIGNALS
from taskmates.types import Chat


class MarkdownCompletionAction:
    async def perform(self, chat: Chat, completion_assistance):
        signals = SIGNALS.get()

        await completion_assistance.perform_completion(chat)

        await self.on_after_step(chat, signals)

    @staticmethod
    async def on_after_step(chat, signals):
        separator = compute_separator(chat['markdown_chat'])
        if separator:
            await signals.response.response.send_async(separator)
