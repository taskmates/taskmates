from taskmates.types import Chat
from taskmates.workflow_engine.environment_signals import EnvironmentSignals
from taskmates.workflows.actions.taskmates_action import TaskmatesAction


class MarkdownCompleteSectionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance, completion_signals: EnvironmentSignals):
        await completion_assistance.perform_completion(chat, completion_signals)
