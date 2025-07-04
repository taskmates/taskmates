from taskmates.core.workflow_engine.base_signals import BaseSignals


class ExecutionEnvironmentSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.error = self.namespace.signal('error')
        self.result = self.namespace.signal('result')
        self.stdout = self.namespace.signal('stdout')
        self.artifact = self.namespace.signal('artifact')
