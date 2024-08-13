import sys
from typing import TextIO
from taskmates.core.handlers.handler import Handler


class StdoutCompletionStreamer(Handler):
    def __init__(self, format: str, output_stream: TextIO = sys.stdout):
        self.format = format
        self.output_stream = output_stream

    async def process_chunk(self, chunk):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True, file=self.output_stream)

    def connect(self, signals):
        if self.format == 'full':
            signals.input.history.connect(self.process_chunk, weak=False)
            signals.input.incoming_message.connect(self.process_chunk, weak=False)
            signals.input.formatting.connect(self.process_chunk, weak=False)
            signals.response.formatting.connect(self.process_chunk, weak=False)
            signals.response.response.connect(self.process_chunk, weak=False)
            signals.response.responder.connect(self.process_chunk, weak=False)
            signals.response.error.connect(self.process_chunk, weak=False)
        elif self.format == 'completion':
            signals.response.responder.connect(self.process_chunk, weak=False)
            signals.response.response.connect(self.process_chunk, weak=False)
            signals.response.error.connect(self.process_chunk, weak=False)
        elif self.format == 'text':
            signals.response.response.connect(self.process_chunk, weak=False)
        else:
            raise ValueError(f"Invalid format: {self.format}")

    def disconnect(self, signals):
        if self.format == 'full':
            signals.input.history.disconnect(self.process_chunk)
            signals.input.incoming_message.disconnect(self.process_chunk)
            signals.input.formatting.disconnect(self.process_chunk)
            signals.response.formatting.disconnect(self.process_chunk)
            signals.response.response.disconnect(self.process_chunk)
            signals.response.responder.disconnect(self.process_chunk)
            signals.response.error.disconnect(self.process_chunk)
        elif self.format == 'completion':
            signals.response.responder.disconnect(self.process_chunk)
            signals.response.response.disconnect(self.process_chunk)
            signals.response.error.disconnect(self.process_chunk)
        elif self.format == 'text':
            signals.response.response.disconnect(self.process_chunk)
        else:
            raise ValueError(f"Invalid format: {self.format}")
