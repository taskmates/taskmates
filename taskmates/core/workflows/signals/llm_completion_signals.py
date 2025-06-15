from taskmates.core.workflow_engine.base_signals import BaseSignals


class LlmCompletionSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.chat_completion = self.namespace.signal('chat_completion')
