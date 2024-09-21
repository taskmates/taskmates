from typing import Any

from taskmates.core.job import Job
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.not_set.not_set import NOT_SET


class ReturnValueHandler(Job):
    def __init__(self):
        self.completion_chunks = []
        self.return_value = NOT_SET
        self.error = None

    async def handle_response_chunk(self, chunk):
        self.completion_chunks.append(chunk)

    async def handle_return_value(self, status):
        self.return_value = status

    async def handle_error(self, payload):
        self.error = payload["error"]

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.response.connect(self.handle_response_chunk)
        signals.outputs.result.connect(self.handle_return_value)
        signals.outputs.error.connect(self.handle_error)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.response.disconnect(self.handle_response_chunk)
        signals.outputs.result.disconnect(self.handle_return_value)
        signals.outputs.error.disconnect(self.handle_error)

    def should_raise_error(self) -> bool:
        return self.error is not None

    def raise_error(self):
        if self.should_raise_error():
            raise self.error

    def get_return_value(self) -> Any:
        if self.should_raise_error():
            self.raise_error()

        if self.return_value is not NOT_SET:
            return self.return_value["result"]
        return "".join(self.completion_chunks)
