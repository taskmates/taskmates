from taskmates.core.compute_separator import compute_separator
from taskmates.signals.handler import Handler
from taskmates.signals.signals import Signals


class IncomingMessagesFormattingProcessor(Handler):
    def __init__(self, signals):
        self.signals = signals

    def connect(self, signals: Signals):
        signals.input.history.connect(self.handle, weak=False)
        signals.input.incoming_message.connect(self.handle, weak=False)

    def disconnect(self, signals: Signals):
        signals.input.history.disconnect(self.handle)
        signals.input.incoming_message.disconnect(self.handle)

    async def handle(self, incoming_content):
        separator = compute_separator(incoming_content)
        if separator:
            await self.signals.input.formatting.send_async(separator)
