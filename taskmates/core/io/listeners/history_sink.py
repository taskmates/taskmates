from taskmates.core.daemon import Daemon
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class HistorySink(Daemon):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.file = None

    async def process_chunk(self, chunk):
        if self.file:
            self.file.write(chunk)
            self.file.flush()

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        if self.path:
            self.file = open(self.path, "a")
            self.exit_stack.callback(self.file.close)

        connections = [
            execution_context.input_streams.incoming_message.connected_to(self.process_chunk),
            execution_context.input_streams.formatting.connected_to(self.process_chunk),
            execution_context.output_streams.stdout.connected_to(self.process_chunk)
        ]

        self.exit_stack.enter_context(stacked_contexts(connections))
