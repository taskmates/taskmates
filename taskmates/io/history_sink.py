from taskmates.core.signal_receiver import SignalReceiver


class HistorySink(SignalReceiver):
    def __init__(self, path):
        self.path = path
        self.file = None

    async def process_chunk(self, chunk):
        if self.file:
            self.file.write(chunk)
            self.file.flush()

    def connect(self, signals):
        if self.path:
            self.file = open(self.path, "a")
        signals.input.incoming_message.connect(self.process_chunk, weak=False)
        signals.input.formatting.connect(self.process_chunk, weak=False)
        signals.response.completion.connect(self.process_chunk, weak=False)

    def disconnect(self, signals):
        signals.input.incoming_message.disconnect(self.process_chunk)
        signals.input.formatting.disconnect(self.process_chunk)
        signals.response.completion.disconnect(self.process_chunk)
        if self.file:
            self.file.close()
