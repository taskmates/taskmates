import functools
from typing import Any

from taskmates.core.daemon import Daemon
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.core.signals.base_signals import BaseSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class SignalsCapturer(Daemon):
    def __init__(self):
        super().__init__()
        self.captured_signals: list[tuple[str, Any]] = []

    async def handle(self, signal_name: str, payload):
        self.captured_signals.append((signal_name, payload))

    async def signal_handler(self, signal_name: str, payload):
        await self.handle(signal_name, payload)

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        connections = []

        for signal_group_name, signal_group in vars(execution_context).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    connections.append(
                        signal.connected_to(
                            functools.partial(self.signal_handler, signal_name)
                        )
                    )

        self.exit_stack.enter_context(stacked_contexts(connections))

    def filter_signals(self, signal_names):
        return [(signal_name, payload) for signal_name, payload in self.captured_signals if signal_name in signal_names]
