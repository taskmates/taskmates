import functools

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.transaction import TRANSACTION, Transaction
from taskmates.core.workflow_engine.base_signals import BaseSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class CapturedSignalsDaemon(CompositeContextManager):
    def __init__(self):
        super().__init__()

    async def capture_signal(self, signal_name: str, payload, run: Transaction):
        run.execution_context.state["captured_signals"].append((signal_name, payload))

    def __enter__(self):
        run = TRANSACTION.get()
        connections = []

        signals = run.signals
        for signal_group_name, signal_group in signals.items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    connections.append(
                        signal.connected_to(
                            functools.partial(self.capture_signal, signal_name, run=run)
                        )
                    )

        if not connections:
            raise ValueError("Nothing to capture")

        self.exit_stack.enter_context(stacked_contexts(connections))
