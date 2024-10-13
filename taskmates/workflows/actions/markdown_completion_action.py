from taskmates.core.compute_separator import compute_separator
from taskmates.workflow_engine.run import RUN
from taskmates.workflows.actions.taskmates_action import TaskmatesAction
from taskmates.types import Chat


class MarkdownCompletionAction(TaskmatesAction):
    async def perform(self, chat: Chat, completion_assistance):
        await completion_assistance.perform_completion(chat)

        await self.on_after_step()

    @staticmethod
    async def on_after_step():
        run = RUN.get()
        markdown_chat = run.state["markdown_chat"].outputs["completion"]
        separator = compute_separator(markdown_chat)
        if separator:
            await run.signals["output_streams"].response.send_async(separator)
