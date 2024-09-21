from taskmates.core.compute_separator import compute_separator
from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT


class IncomingMessagesFormattingProcessor(Job):
    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.inputs.history.connect(self.handle, weak=False)
        signals.inputs.incoming_message.connect(self.handle, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.inputs.history.disconnect(self.handle)
        signals.inputs.incoming_message.disconnect(self.handle)

    async def handle(self, incoming_content):
        separator = compute_separator(incoming_content)
        if separator:
            await EXECUTION_CONTEXT.get().inputs.formatting.send_async(separator)
