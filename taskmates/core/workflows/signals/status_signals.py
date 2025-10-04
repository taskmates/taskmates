from taskmates.core.workflow_engine.base_signals import BaseSignals


class StatusSignals(BaseSignals):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interrupted = self.namespace.signal('interrupted')
        self.killed = self.namespace.signal('killed')
