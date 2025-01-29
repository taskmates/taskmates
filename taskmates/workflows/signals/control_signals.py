from taskmates.workflow_engine.base_signals import BaseSignals


class ControlSignals(BaseSignals):

    def __init__(self):
        super().__init__()
        self.interrupt_request = self.namespace.signal('interrupt_request')
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')
