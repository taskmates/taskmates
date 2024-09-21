from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT


class HistorySink(Job):
    def __init__(self, path):
        self.path = path
        self.file = None

    async def process_chunk(self, chunk):
        if self.file:
            self.file.write(chunk)
            self.file.flush()

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        if self.path:
            self.file = open(self.path, "a")
        signals.inputs.incoming_message.connect(self.process_chunk, weak=False)
        signals.inputs.formatting.connect(self.process_chunk, weak=False)
        signals.outputs.stdout.connect(self.process_chunk, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.inputs.incoming_message.disconnect(self.process_chunk)
        signals.inputs.formatting.disconnect(self.process_chunk)
        signals.outputs.stdout.disconnect(self.process_chunk)
        if self.file:
            self.file.close()
