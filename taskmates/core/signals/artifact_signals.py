from taskmates.core.signals.base_signals import BaseSignals


class ArtifactSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.artifact = self.namespace.signal('artifact')
