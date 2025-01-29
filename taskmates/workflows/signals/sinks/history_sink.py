from taskmates.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.workflow_engine.run import RUN
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class HistorySink(CompositeContextManager):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.file = None

    async def process_chunk(self, chunk):
        if self.file:
            self.file.write(chunk)
            self.file.flush()

    def __enter__(self):
        run = RUN.get()
        if self.path:
            self.file = open(self.path, "a")
            self.exit_stack.callback(self.file.close)

        connections = [
            run.signals["input_streams"].incoming_message.connected_to(self.process_chunk),
            run.signals["input_streams"].formatting.connected_to(self.process_chunk),
            run.signals["execution_environment"].stdout.connected_to(self.process_chunk)
        ]

        self.exit_stack.enter_context(stacked_contexts(connections))
