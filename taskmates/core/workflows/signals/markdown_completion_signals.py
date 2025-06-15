from taskmates.core.workflow_engine.base_signals import BaseSignals


class MarkdownCompletionSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.formatting = self.namespace.signal('response_formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.next_responder = self.namespace.signal('next_responder')
