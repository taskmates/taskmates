from taskmates.core.signal_receiver import SignalReceiver


class CurrentMarkdown(SignalReceiver):
    def __init__(self, current_markdown=None):
        self.markdown_chunks = []
        if current_markdown is not None:
            self.markdown_chunks.append(current_markdown)

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get(self):
        return "".join(self.markdown_chunks)

    def connect(self, signals):
        signals.input.history.connect(self.handle, weak=False)
        signals.input.incoming_message.connect(self.handle, weak=False)
        signals.input.formatting.connect(self.handle, weak=False)
        signals.response.formatting.connect(self.handle, weak=False)
        signals.response.response.connect(self.handle, weak=False)
        signals.response.responder.connect(self.handle, weak=False)
        signals.response.error.connect(self.handle, weak=False)

    def disconnect(self, signals):
        signals.input.history.disconnect(self.handle)
        signals.input.incoming_message.disconnect(self.handle)
        signals.input.formatting.disconnect(self.handle)
        signals.response.formatting.disconnect(self.handle)
        signals.response.response.disconnect(self.handle)
        signals.response.responder.disconnect(self.handle)
        signals.response.error.disconnect(self.handle)
