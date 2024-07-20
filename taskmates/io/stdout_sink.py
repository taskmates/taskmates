class StdoutSink:
    def __init__(self, format):
        self.format = format

    def connect(self, signals):
        async def process_chunk(chunk):
            if isinstance(chunk, str):
                print(chunk, end="", flush=True)

        if self.format == 'full':
            signals.output.request.connect(process_chunk, weak=False)
            signals.output.formatting.connect(process_chunk, weak=False)
            signals.output.responder.connect(process_chunk, weak=False)
            signals.output.response.connect(process_chunk, weak=False)
            signals.output.error.connect(process_chunk, weak=False)
        elif self.format == 'original':
            signals.output.request.connect(process_chunk, weak=False)
        elif self.format == 'completion':
            signals.output.responder.connect(process_chunk, weak=False)
            signals.output.response.connect(process_chunk, weak=False)
            signals.output.error.connect(process_chunk, weak=False)
        elif self.format == 'text':
            signals.output.response.connect(process_chunk, weak=False)
        else:
            raise ValueError(f"Invalid format: {self.format}")
