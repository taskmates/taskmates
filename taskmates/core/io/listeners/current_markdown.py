from taskmates.core.processor import Processor
from taskmates.core.execution_environment import EXECUTION_ENVIRONMENT


class CurrentMarkdown(Processor):
    def __init__(self, current_markdown=None):
        self.markdown_chunks = []
        if current_markdown is not None:
            self.markdown_chunks.append(current_markdown)

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get(self):
        return "".join(self.markdown_chunks)

    def __enter__(self):
        signals = EXECUTION_ENVIRONMENT.get().signals
        signals.cli_input.history.connect(self.handle, weak=False)
        signals.cli_input.incoming_message.connect(self.handle, weak=False)
        signals.cli_input.formatting.connect(self.handle, weak=False)
        signals.response.formatting.connect(self.handle, weak=False)
        signals.response.response.connect(self.handle, weak=False)
        signals.response.responder.connect(self.handle, weak=False)
        signals.response.error.connect(self.handle, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_ENVIRONMENT.get().signals
        signals.cli_input.history.disconnect(self.handle)
        signals.cli_input.incoming_message.disconnect(self.handle)
        signals.cli_input.formatting.disconnect(self.handle)
        signals.response.formatting.disconnect(self.handle)
        signals.response.response.disconnect(self.handle)
        signals.response.responder.disconnect(self.handle)
        signals.response.error.disconnect(self.handle)
