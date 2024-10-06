from taskmates.core.daemon import Daemon
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.not_set.not_set import NOT_SET


class ReturnValue(Daemon):
    def __init__(self):
        super().__init__()
        self.stdout_chunks = []
        self.return_value = NOT_SET
        self.error = None

    def get(self):
        return self.return_value

    async def handle_stdout_chunk(self, chunk):
        self.stdout_chunks.append(chunk)

    async def handle_return_value(self, status):
        self.return_value = status

    async def handle_error(self, error):
        self.error = error

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        self.exit_stack.enter_context(stacked_contexts([
            # execution_context.output_streams.stdout.connected_to(self.handle_stdout_chunk),
            execution_context.output_streams.result.connected_to(self.handle_return_value),
            # execution_context.output_streams.error.connected_to(self.handle_error)
        ]))

    def _should_raise_error(self) -> bool:
        return self.error is not None

    def _raise_error(self):
        if self._should_raise_error():
            raise self.error

    # def get(self) -> Any:
    #     if self._should_raise_error():
    #         self._raise_error()
    #
    #     if self.return_value is not NOT_SET:
    #         return self.return_value
    #     return "".join(self.stdout_chunks)

    def get_result(self):
        return self.return_value
