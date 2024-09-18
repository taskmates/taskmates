from taskmates.core.processor import Processor
from taskmates.core.execution_context import EXECUTION_CONTEXT


class HistorySink(Processor):
    def __init__(self, path):
        self.path = path
        self.file = None

    async def process_chunk(self, chunk):
        if self.file:
            self.file.write(chunk)
            self.file.flush()

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        if self.path:
            self.file = open(self.path, "a")
        signals.cli_input.incoming_message.connect(self.process_chunk, weak=False)
        signals.cli_input.formatting.connect(self.process_chunk, weak=False)
        signals.response.stdout.connect(self.process_chunk, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.cli_input.incoming_message.disconnect(self.process_chunk)
        signals.cli_input.formatting.disconnect(self.process_chunk)
        signals.response.stdout.disconnect(self.process_chunk)
        if self.file:
            self.file.close()
