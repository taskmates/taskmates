import sys
from typing import TextIO

from taskmates.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.workflow_engine.run import RUN
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class WriteMarkdownChatToStdout(CompositeContextManager):
    def __init__(self, format: str, output_stream: TextIO = sys.stdout):
        super().__init__()
        self.format = format
        self.output_stream = output_stream

    async def process_chunk(self, chunk):
        if isinstance(chunk, str):
            print(chunk, end="", flush=True, file=self.output_stream)

    def __enter__(self):
        run = RUN.get()
        connections = []

        if self.format == 'full':
            connections.extend([
                run.signals["input_streams"].history.connected_to(self.process_chunk),
                run.signals["input_streams"].incoming_message.connected_to(self.process_chunk),
                run.signals["input_streams"].formatting.connected_to(self.process_chunk),
                run.signals["markdown_completion"].formatting.connected_to(self.process_chunk),
                run.signals["markdown_completion"].response.connected_to(self.process_chunk),
                run.signals["markdown_completion"].responder.connected_to(self.process_chunk),
                run.signals["execution_environment"].error.connected_to(self.process_chunk)
            ])
        elif self.format == 'completion':
            connections.extend([
                run.signals["markdown_completion"].responder.connected_to(self.process_chunk),
                run.signals["markdown_completion"].response.connected_to(self.process_chunk),
                run.signals["execution_environment"].error.connected_to(self.process_chunk)
            ])
        elif self.format == 'text':
            connections.append(run.signals["markdown_completion"].response.connected_to(self.process_chunk))
        else:
            raise ValueError(f"Invalid format: {self.format}")

        self.exit_stack.enter_context(stacked_contexts(connections))
