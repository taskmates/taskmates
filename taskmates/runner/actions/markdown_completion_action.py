from taskmates.core.compute_separator import compute_separator
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.runner.actions.taskmates_action import TaskmatesAction
from taskmates.types import Chat


class MarkdownCompletionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance):
        signals = EXECUTION_CONTEXT.get().signals

        await completion_assistance.perform_completion(chat)

        await self.on_after_step(chat, signals)

    @staticmethod
    async def on_after_step(chat, signals):
        separator = compute_separator(chat['markdown_chat'])
        if separator:
            await signals.response.response.send_async(separator)
