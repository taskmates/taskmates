import os

from loguru import logger
from typeguard import typechecked

from taskmates.core.signal_receivers.current_markdown import CurrentMarkdown
from taskmates.core.signals import SIGNALS, Signals
from taskmates.io.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.io.history_sink import HistorySink
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.defaults.workflows.taskmates_workflow import TaskmatesWorkflow


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

        signals = SIGNALS.get(Signals())

        current_markdown = CurrentMarkdown()
        with signals.connected_to([
            current_markdown,
            HistorySink(history_path),
            IncomingMessagesFormattingProcessor(),
        ]):
            if history_path:
                history = read_history(history_path)
                if history:
                    await signals.input.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.input.incoming_message.send_async(incoming_message)

        handlers = await self.build_handlers(response_format, history_path)

        try:
            with signals.connected_to(handlers) as signals:
                result = await MarkdownComplete().run(
                    current_markdown=current_markdown.get()
                )

            return result
        except Exception as e:
            await signals.response.error.send_async(e)
            logger.error(e)

    async def build_handlers(self,
                             response_format: str,
                             history_path: str):
        handlers = [
            SigIntAndSigTermController(),
            StdoutCompletionStreamer(response_format),
            HistorySink(history_path)
        ]
        return handlers
