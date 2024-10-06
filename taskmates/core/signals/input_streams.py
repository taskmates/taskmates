from taskmates.core.signals.base_signals import BaseSignals


class InputStreams(BaseSignals):
    def __init__(self):
        super().__init__()
        self.history = self.namespace.signal('history')
        self.incoming_message = self.namespace.signal('incoming_message')
        self.formatting = self.namespace.signal('input_formatting')
