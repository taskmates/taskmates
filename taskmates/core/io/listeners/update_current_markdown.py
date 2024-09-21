from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.core.job import Job


class UpdateCurrentMarkdown(Job):
    def __init__(self):
        self.markdown_chunks = []

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get(self):
        return "".join(self.markdown_chunks)

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        if execution_context.workflow_inputs.get("current_markdown") is not None:
            self.markdown_chunks.append(execution_context.workflow_inputs.get("current_markdown"))

        execution_context.inputs.history.connect(self.handle, weak=False)
        execution_context.inputs.incoming_message.connect(self.handle, weak=False)
        execution_context.inputs.formatting.connect(self.handle, weak=False)
        execution_context.outputs.formatting.connect(self.handle, weak=False)
        execution_context.outputs.response.connect(self.handle, weak=False)
        execution_context.outputs.responder.connect(self.handle, weak=False)
        execution_context.outputs.error.connect(self.handle, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_context = EXECUTION_CONTEXT.get()
        execution_context.inputs.history.disconnect(self.handle)
        execution_context.inputs.incoming_message.disconnect(self.handle)
        execution_context.inputs.formatting.disconnect(self.handle)
        execution_context.outputs.formatting.disconnect(self.handle)
        execution_context.outputs.response.disconnect(self.handle)
        execution_context.outputs.responder.disconnect(self.handle)
        execution_context.outputs.error.disconnect(self.handle)
