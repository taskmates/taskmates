from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT


class RaiseErrorCollector(Job):
    def __init__(self):
        self.error = None

    async def handle_error(self, payload):
        self.error = payload["error"]

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.error.connect(self.handle_error)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.error.disconnect(self.handle_error)

    def get_error(self):
        return self.error
