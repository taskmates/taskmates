from taskmates.core.signal_receiver import SignalReceiver
from taskmates.lib.not_set.not_set import NOT_SET


class ReturnValueCollector(SignalReceiver):
    def __init__(self):
        self.return_value = NOT_SET

    async def handle_return_value(self, status):
        self.return_value = status

    def connect(self, signals):
        signals.output.result.connect(self.handle_return_value)

    def disconnect(self, signals):
        signals.output.result.disconnect(self.handle_return_value)

    def get_result(self):
        return self.return_value
