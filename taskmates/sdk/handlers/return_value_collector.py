from taskmates.core.processor import Processor
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.not_set.not_set import NOT_SET


class ReturnValueCollector(Processor):
    def __init__(self):
        self.return_value = NOT_SET

    async def handle_return_value(self, status):
        self.return_value = status

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.response.result.connect(self.handle_return_value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.response.result.disconnect(self.handle_return_value)

    def get_result(self):
        return self.return_value
