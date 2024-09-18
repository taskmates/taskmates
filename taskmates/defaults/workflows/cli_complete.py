import os

from loguru import logger
from typeguard import typechecked

from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.core.io.emitters.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.core.io.listeners.current_markdown import CurrentMarkdown
from taskmates.core.io.listeners.history_sink import HistorySink
from taskmates.core.io.listeners.stdout_completion_streamer import StdoutCompletionStreamer
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
        try:
            current_markdown = await self.get_incoming_markdown(history_path, incoming_messages)

            processors = await self.build_handlers(response_format, history_path)

            # TODO: build a new Contexts object here
            result = await MarkdownComplete(contexts=self.execution_context.contexts, processors=processors).run(
                current_markdown=current_markdown
            )

            return result

        # TODO: move this to EXECUTION_ENVIRONMENT
        except Exception as e:
            signals = EXECUTION_CONTEXT.get().signals
            await signals.response.error.send_async(e)
            raise e
            logger.error(e)

    async def get_incoming_markdown(self, history_path, incoming_messages):
        signals = EXECUTION_CONTEXT.get().signals
        incoming_markdown = CurrentMarkdown()
        cli_history_processors = [
            incoming_markdown,
            HistorySink(history_path),
            IncomingMessagesFormattingProcessor(),
        ]
        # TODO: replace this with an ExecutionEnvironment context
        with stacked_contexts(cli_history_processors):
            if history_path:
                history = read_history(history_path)
                if history:
                    await signals.cli_input.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.cli_input.incoming_message.send_async(incoming_message)
        current_markdown = incoming_markdown.get()
        return current_markdown

    async def build_handlers(self,
                             response_format: str,
                             history_path: str):
        handlers = [
            SigIntAndSigTermController(),
            StdoutCompletionStreamer(response_format),
            HistorySink(history_path)
        ]
        return handlers
