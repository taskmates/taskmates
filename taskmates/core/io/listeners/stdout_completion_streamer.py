import sys
from typing import TextIO

from taskmates.core.daemon import Daemon
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class StdoutCompletionStreamer(Daemon):
    def __init__(self, format: str, output_stream: TextIO = sys.stdout):
        super().__init__()
        self.format = format
        self.output_stream = output_stream

    async def process_chunk(self, chunk):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True, file=self.output_stream)

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        connections = []

        if self.format == 'full':
            connections.extend([
                execution_context.inputs.history.connected_to(self.process_chunk),
                execution_context.inputs.incoming_message.connected_to(self.process_chunk),
                execution_context.inputs.formatting.connected_to(self.process_chunk),
                execution_context.outputs.formatting.connected_to(self.process_chunk),
                execution_context.outputs.response.connected_to(self.process_chunk),
                execution_context.outputs.responder.connected_to(self.process_chunk),
                execution_context.outputs.error.connected_to(self.process_chunk)
            ])
        elif self.format == 'completion':
            connections.extend([
                execution_context.outputs.responder.connected_to(self.process_chunk),
                execution_context.outputs.response.connected_to(self.process_chunk),
                execution_context.outputs.error.connected_to(self.process_chunk)
            ])
        elif self.format == 'text':
            connections.append(execution_context.outputs.response.connected_to(self.process_chunk))
        else:
            raise ValueError(f"Invalid format: {self.format}")

        self.exit_stack.enter_context(stacked_contexts(connections))
