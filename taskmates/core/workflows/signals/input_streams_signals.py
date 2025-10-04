from taskmates.core.workflow_engine.base_signals import BaseSignals


class InputStreamsSignals(BaseSignals):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request = self.namespace.signal('request')
