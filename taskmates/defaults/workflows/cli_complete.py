import os

from typeguard import typechecked

from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.core.io.emitters.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.core.io.listeners.history_sink import HistorySink
from taskmates.core.io.listeners.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.core.io.listeners.update_current_markdown import UpdateCurrentMarkdown
from taskmates.core.io.mediators.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


def read_history(history_path):
    history = ""
    if history_path:
        if not os.path.exists(history_path):
            return None
        with open(history_path, 'r') as f:
            history = f.read()
    return history


class CliComplete(TaskmatesWorkflow):
    @typechecked
    async def run(self,
                  incoming_messages: list[str],
                  response_format: str = "text",
                  history_path: str | None = None
                  ):
        current_markdown = await self.get_incoming_markdown(history_path, incoming_messages)

        jobs = [
            SigIntAndSigTermController(),
            StdoutCompletionStreamer(response_format),
            HistorySink(history_path)
        ]

        # TODO: build a new Contexts object here
        result = await MarkdownComplete(contexts=self.execution_context.contexts, jobs=jobs).run(
            current_markdown=current_markdown
        )

        return result

        # try:
        # # TODO: move this to EXECUTION_ENVIRONMENT
        # except Exception as e:
        #     signals = EXECUTION_CONTEXT.get()
        #     await signals.outputs.error.send_async(e)
        #     raise e
        #     logger.error(e)

    async def get_incoming_markdown(self, history_path, incoming_messages):
        signals = EXECUTION_CONTEXT.get()
        incoming_markdown = UpdateCurrentMarkdown()
        cli_history_jobs = [
            incoming_markdown,
            HistorySink(history_path),
            IncomingMessagesFormattingProcessor(),
        ]
        # TODO: replace this with an ExecutionEnvironment context
        with stacked_contexts(cli_history_jobs):
            if history_path:
                history = read_history(history_path)
                if history:
                    await signals.inputs.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.inputs.incoming_message.send_async(incoming_message)
        current_markdown = incoming_markdown.get()
        return current_markdown
