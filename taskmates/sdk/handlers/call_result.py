from typing import Any

from taskmates.core.execution_context import EXECUTION_CONTEXT, ExecutionContext
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class CallResult(ExecutionContext):
    def __init__(self):
        super().__init__()
        self.completion_chunks = []
        self.return_value = NOT_SET
        self.error = None

    async def handle_stdout_chunk(self, chunk):
        self.completion_chunks.append(chunk)

    async def handle_return_value(self, status):
        self.return_value = status

    async def handle_error(self, payload):
        self.error = payload["error"]

    def __enter__(self):
        execution_context: ExecutionContext = EXECUTION_CONTEXT.get()
        self.exit_stack.enter_context(stacked_contexts([
            execution_context.output_streams.response.connected_to(self.handle_stdout_chunk),
            execution_context.output_streams.result.connected_to(self.handle_return_value),
            execution_context.output_streams.error.connected_to(self.handle_error)
        ]))

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
