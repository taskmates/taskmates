from taskmates.workflow_engine.base_signals import BaseSignals
from taskmates.workflow_engine.signal_direction import SignalDirection


class ControlSignals(BaseSignals):
    signal_direction = SignalDirection.DOWNSTREAM

    def __init__(self):
        super().__init__()
        self.interrupt_request = self.namespace.signal('interrupt_request')
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')
