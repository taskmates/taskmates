from taskmates.core.compute_separator import compute_separator
from taskmates.core.execution_context import EXECUTION_CONTEXT, ExecutionContext
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class IncomingMessagesFormattingProcessor(ExecutionContext):
    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        self.exit_stack.enter_context(stacked_contexts([
            execution_context.input_streams.history.connected_to(self.handle),
            execution_context.input_streams.incoming_message.connected_to(self.handle)
        ]))

    async def handle(self, incoming_content):
        separator = compute_separator(incoming_content)
        if separator:
            await EXECUTION_CONTEXT.get().input_streams.formatting.send_async(separator)
