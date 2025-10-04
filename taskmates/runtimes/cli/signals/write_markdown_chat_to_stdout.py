import sys
from typing import TextIO

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.input_streams_signals import InputStreamsSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class WriteMarkdownChatToStdout(CompositeContextManager):
    def __init__(self,
                 execution_environment_signals: ExecutionEnvironmentSignals,
                 input_streams_signals: InputStreamsSignals,
                 format: str, output_stream: TextIO = sys.stdout):
        super().__init__()
        self.execution_environment_signals = execution_environment_signals
        self.execution_environment_signals = execution_environment_signals
        self.input_streams_signals = input_streams_signals

        self.format = format
        self.output_stream = output_stream

    async def process_chunk(self, sender, value):
        if isinstance(value, str):
            print(value, end="", flush=True, file=self.output_stream)

    def __enter__(self):
        connections = []

        if self.format == 'full':
            connections.extend([
                self.input_streams_signals.request.connected_to(self.process_chunk, sender="history"),
                self.input_streams_signals.request.connected_to(self.process_chunk, sender="incoming_message"),
                self.input_streams_signals.request.connected_to(self.process_chunk, sender="formatting"),
                self.execution_environment_signals.response.connected_to(self.process_chunk, sender="formatting"),
                self.execution_environment_signals.response.connected_to(self.process_chunk, sender="response"),
                self.execution_environment_signals.response.connected_to(self.process_chunk, sender="responder"),
                self.execution_environment_signals.error.connected_to(self.process_chunk)
            ])
        elif self.format == 'completion':
            connections.extend([
                self.execution_environment_signals.response.connected_to(self.process_chunk, sender="responder"),
                self.execution_environment_signals.response.connected_to(self.process_chunk, sender="response"),
                self.execution_environment_signals.error.connected_to(self.process_chunk)
            ])
        elif self.format == 'text':
            connections.append(self.execution_environment_signals.response.connected_to(self.process_chunk, sender="response"))
        else:
            raise ValueError(f"Invalid format: {self.format}")

        self.exit_stack.enter_context(stacked_contexts(connections))
