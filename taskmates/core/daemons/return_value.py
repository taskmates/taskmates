from taskmates.core.execution_context import ExecutionContext, EXECUTION_CONTEXT
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class ReturnValue(ExecutionContext):
    def __init__(self):
        super().__init__()
        self.return_value = NOT_SET

    def get(self):
        return self.return_value

    async def handle_return_value(self, status):
        self.return_value = status

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        self.exit_stack.enter_context(stacked_contexts([
            execution_context.outputs.result.connected_to(self.handle_return_value)
        ]))

    def get_result(self):
        return self.return_value
