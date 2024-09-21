import sys
from typing import TextIO
from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT


class StdoutCompletionStreamer(Job):
    def __init__(self, format: str, output_stream: TextIO = sys.stdout):
        self.format = format
        self.output_stream = output_stream

    async def process_chunk(self, chunk):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True, file=self.output_stream)

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        if self.format == 'full':
            signals.inputs.history.connect(self.process_chunk, weak=False)
            signals.inputs.incoming_message.connect(self.process_chunk, weak=False)
            signals.inputs.formatting.connect(self.process_chunk, weak=False)
            signals.outputs.formatting.connect(self.process_chunk, weak=False)
            signals.outputs.response.connect(self.process_chunk, weak=False)
            signals.outputs.responder.connect(self.process_chunk, weak=False)
            signals.outputs.error.connect(self.process_chunk, weak=False)
        elif self.format == 'completion':
            signals.outputs.responder.connect(self.process_chunk, weak=False)
            signals.outputs.response.connect(self.process_chunk, weak=False)
            signals.outputs.error.connect(self.process_chunk, weak=False)
        elif self.format == 'text':
            signals.outputs.response.connect(self.process_chunk, weak=False)
        else:
            raise ValueError(f"Invalid format: {self.format}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        if self.format == 'full':
            signals.inputs.history.disconnect(self.process_chunk)
            signals.inputs.incoming_message.disconnect(self.process_chunk)
            signals.inputs.formatting.disconnect(self.process_chunk)
            signals.outputs.formatting.disconnect(self.process_chunk)
            signals.outputs.response.disconnect(self.process_chunk)
            signals.outputs.responder.disconnect(self.process_chunk)
            signals.outputs.error.disconnect(self.process_chunk)
        elif self.format == 'completion':
            signals.outputs.responder.disconnect(self.process_chunk)
            signals.outputs.response.disconnect(self.process_chunk)
            signals.outputs.error.disconnect(self.process_chunk)
        elif self.format == 'text':
            signals.outputs.response.disconnect(self.process_chunk)
        else:
            raise ValueError(f"Invalid format: {self.format}")
