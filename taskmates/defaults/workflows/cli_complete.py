import os

from typeguard import typechecked

from taskmates.core.io.listeners.history_sink import HistorySink
from taskmates.core.io.listeners.markdown_chat import MarkdownChat
from taskmates.core.io.mediators.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.core.run import RUN
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.runner.contexts.runner_context import RunnerContext


def read_history(history_path):
    history = ""
    if history_path:
        if not os.path.exists(history_path):
            return None
        with open(history_path, 'r') as f:
            history = f.read()
    return history


class CliComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: RunnerContext = None,
                 ):
        super().__init__(contexts=contexts)

    @typechecked
    async def run(self,
                  incoming_messages: list[str],
                  response_format: str = "text",
                  history_path: str | None = None
                  ):
        markdown_chat = await self.get_incoming_markdown(history_path, incoming_messages)

        # TODO: build a new RunnerContext object here
        result = await MarkdownComplete().run(
            markdown_chat=markdown_chat
        )

        return result

        # try:
        # # TODO: move this to EXECUTION_ENVIRONMENT
        # except Exception as e:
        #     signals = RUN.get()
        #     await signals.output_streams.error.send_async(e)
        #     raise e
        #     logger.error(e)

    async def get_incoming_markdown(self, history_path, incoming_messages) -> str:
        signals = RUN.get()
        incoming_markdown = MarkdownChat()
        cli_history_jobs = [
            incoming_markdown,
            IncomingMessagesFormattingProcessor(),
        ]
        # TODO: replace this with an ExecutionEnvironment context
        with stacked_contexts(cli_history_jobs):
            if history_path:
                history = read_history(history_path)
                if history:
                    await signals.input_streams.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.input_streams.incoming_message.send_async(incoming_message)
        markdown_chat = incoming_markdown.get()["full"]
        return markdown_chat
