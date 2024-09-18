from taskmates.core.compute_separator import compute_separator
from taskmates.core.processor import Processor
from taskmates.core.execution_context import EXECUTION_CONTEXT


class IncomingMessagesFormattingProcessor(Processor):
    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.cli_input.history.connect(self.handle, weak=False)
        signals.cli_input.incoming_message.connect(self.handle, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.cli_input.history.disconnect(self.handle)
        signals.cli_input.incoming_message.disconnect(self.handle)

    async def handle(self, incoming_content):
        separator = compute_separator(incoming_content)
        if separator:
            await EXECUTION_CONTEXT.get().signals.cli_input.formatting.send_async(separator)
