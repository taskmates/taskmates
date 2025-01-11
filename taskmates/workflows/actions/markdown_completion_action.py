from taskmates.types import Chat
from taskmates.workflows.actions.taskmates_action import TaskmatesAction


class MarkdownCompletionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance):
        await completion_assistance.perform_completion(chat)
