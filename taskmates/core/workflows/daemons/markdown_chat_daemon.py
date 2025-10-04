import functools

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class MarkdownChatDaemon(CompositeContextManager):
    def __init__(self,
                 execution_environment_signals: ExecutionEnvironmentSignals,
                 markdown_chat_state: MarkdownChat):
        super().__init__()
        self.execution_environment_signals = execution_environment_signals
        self.markdown_chat_state = markdown_chat_state

    async def process_chunk(self, sender, value: str, format: str):
        self.markdown_chat_state.append_to_format(format, value)

    def __enter__(self):
        connections = []
        connections.extend([
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="history"),
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="incoming_message"),
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="formatting"),
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="response"),
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="responder"),
            self.execution_environment_signals.error.connected_to(
                functools.partial(self.process_chunk, format="full"), sender="error"),
        ])
        connections.extend([
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="completion"), sender="responder"),
            self.execution_environment_signals.response.connected_to(
                functools.partial(self.process_chunk, format="completion"), sender="response"),
            self.execution_environment_signals.error.connected_to(
                functools.partial(self.process_chunk, format="completion"), sender="error")
        ])
        connections.append(self.execution_environment_signals.response.connected_to(
            functools.partial(self.process_chunk, format="text"), sender="response"))

        self.exit_stack.enter_context(stacked_contexts(connections))
