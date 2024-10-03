from taskmates.core.execution_context import EXECUTION_CONTEXT, ExecutionContext
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class MarkdownChat(ExecutionContext):
    def __init__(self):
        super().__init__()
        self.markdown_chunks = []

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get(self):
        return "".join(self.markdown_chunks)

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        if execution_context.workflow_inputs.get("markdown_chat") is not None:
            self.markdown_chunks.append(execution_context.workflow_inputs.get("markdown_chat"))

        self.exit_stack.enter_context(stacked_contexts([
            execution_context.inputs.history.connected_to(self.handle),
            execution_context.inputs.incoming_message.connected_to(self.handle),
            execution_context.inputs.formatting.connected_to(self.handle),
            execution_context.outputs.formatting.connected_to(self.handle),
            execution_context.outputs.response.connected_to(self.handle),
            execution_context.outputs.responder.connected_to(self.handle),
            execution_context.outputs.error.connected_to(self.handle)
        ]))
