import functools
from typing import Any

from taskmates.core.processor import Processor
from taskmates.core.signals.base_signals import BaseSignals
from taskmates.core.execution_environment import EXECUTION_ENVIRONMENT


class SignalsCapturer(Processor):
    def __init__(self):
        self.captured_signals: list[tuple[str, Any]] = []

    async def handle(self, signal_name: str, payload):
        self.captured_signals.append((signal_name, payload))

    async def signal_handler(self, signal_name: str, payload):
        await self.handle(signal_name, payload)

    def __enter__(self):
        signals = EXECUTION_ENVIRONMENT.get().signals
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.connect(
                        functools.partial(self.signal_handler, signal_name),
                        weak=False
                    )

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_ENVIRONMENT.get().signals
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.disconnect(self.signal_handler)

    def filter_signals(self, signal_names):
        return [(signal_name, payload) for signal_name, payload in self.captured_signals if signal_name in signal_names]
