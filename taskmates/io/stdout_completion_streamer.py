from taskmates.cli.lib.handler import Handler


class StdoutCompletionStreamer(Handler):
    def __init__(self, format):
        self.format = format

    def connect(self, signals):
        async def process_chunk(chunk):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)

        if self.format == 'full':
            signals.input.input.connect(process_chunk, weak=False)
            signals.response.formatting.connect(process_chunk, weak=False)
            signals.response.response.connect(process_chunk, weak=False)
            signals.response.responder.connect(process_chunk, weak=False)
            signals.response.error.connect(process_chunk, weak=False)
        elif self.format == 'original':
            signals.input.input.connect(process_chunk, weak=False)
        elif self.format == 'completion':
            signals.response.responder.connect(process_chunk, weak=False)
            signals.response.response.connect(process_chunk, weak=False)
            signals.response.error.connect(process_chunk, weak=False)
        elif self.format == 'text':
            signals.response.response.connect(process_chunk, weak=False)
        else:
            raise ValueError(f"Invalid format: {self.format}")

    def disconnect(self, signals):
        if self.format == 'full':
            signals.input.input.disconnect()
            signals.response.formatting.disconnect()
            signals.response.response.disconnect()
            signals.response.responder.disconnect()
            signals.response.error.disconnect()
        elif self.format == 'original':
            signals.input.input.disconnect()
        elif self.format == 'completion':
            signals.response.responder.disconnect()
            signals.response.response.disconnect()
            signals.response.error.disconnect()
        elif self.format == 'text':
            signals.response.response.disconnect()
        else:
            raise ValueError(f"Invalid format: {self.format}")
