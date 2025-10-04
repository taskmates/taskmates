from taskmates.core.workflow_engine.base_signals import BaseSignals


class LlmChatCompletionSignals(BaseSignals):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm_chat_completion = self.namespace.signal('llm_chat_completion')
