from taskmates.workflow_engine.base_signals import BaseSignals


class StatusSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.start = self.namespace.signal('start')
        self.finish = self.namespace.signal('finish')
        self.success = self.namespace.signal('success')
        self.interrupted = self.namespace.signal('interrupted')
        self.killed = self.namespace.signal('killed')
