from icecream import ic

from taskmates.core.markdown_chat.compute_trailing_newlines import compute_trailing_newlines
from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.input_streams_signals import InputStreamsSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class IncomingMessagesFormattingProcessor(CompositeContextManager):
    def __init__(self, execution_environment_signals: ExecutionEnvironmentSignals):
        super().__init__()
        self.execution_environment_signals = execution_environment_signals

    def __enter__(self):
        self.exit_stack.enter_context(stacked_contexts([
            self.execution_environment_signals.response.connected_to(self.handle, sender="history"),
            self.execution_environment_signals.response.connected_to(self.handle, sender="incoming_message")
        ]))

    async def handle(self, sender, value):
        newlines = compute_trailing_newlines(value)
        if newlines:
            await self.execution_environment_signals.response.send_async(sender="formatting", value=newlines)
