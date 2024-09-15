from taskmates.core.signals.base_signals import BaseSignals


class LifecycleSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.start = self.namespace.signal('start')
        self.finish = self.namespace.signal('finish')
        self.success = self.namespace.signal('success')
        self.interrupted = self.namespace.signal('interrupted')
        self.killed = self.namespace.signal('killed')
