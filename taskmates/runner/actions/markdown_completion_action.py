from taskmates.core.compute_separator import compute_separator
from taskmates.core.execution_context import EXECUTION_CONTEXT, ExecutionContext

from taskmates.runner.actions.taskmates_action import TaskmatesAction
from taskmates.types import Chat


class MarkdownCompletionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance):
        execution_context = EXECUTION_CONTEXT.get()

        await completion_assistance.perform_completion(chat)

        await self.on_after_step(chat, execution_context)

    @staticmethod
    async def on_after_step(chat: Chat, execution_context: ExecutionContext):
        separator = compute_separator(chat['markdown_chat'])
        if separator:
            await execution_context.outputs.response.send_async(separator)
