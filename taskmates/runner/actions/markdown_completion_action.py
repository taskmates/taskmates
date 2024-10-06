from taskmates.core.compute_separator import compute_separator
from taskmates.core.run import RUN, Run

from taskmates.runner.actions.taskmates_action import TaskmatesAction
from taskmates.types import Chat


class MarkdownCompletionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance):
        run = RUN.get()

        await completion_assistance.perform_completion(chat)

        await self.on_after_step(chat, run)

    @staticmethod
    async def on_after_step(chat: Chat, run: Run):
        separator = compute_separator(chat['markdown_chat'])
        if separator:
            await run.output_streams.response.send_async(separator)
