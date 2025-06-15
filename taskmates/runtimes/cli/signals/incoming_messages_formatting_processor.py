from taskmates.core.markdown_chat.compute_separator import compute_separator
from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.run import RUN
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class IncomingMessagesFormattingProcessor(CompositeContextManager):
    def __enter__(self):
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.signals["input_streams"].history.connected_to(self.handle),
            run.signals["input_streams"].incoming_message.connected_to(self.handle)
        ]))

    async def handle(self, incoming_content):
        separator = compute_separator(incoming_content)
        if separator:
            await RUN.get().signals["input_streams"].formatting.send_async(separator)
