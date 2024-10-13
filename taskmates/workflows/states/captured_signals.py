from typing import Any


class CapturedSignals:
    def __init__(self):
        self.captured_signals: list[tuple[str, Any]] = []

    def append(self, signal: tuple[str, Any]):
        self.captured_signals.append(signal)

    def get(self):
        return self.captured_signals

    def filter_signals(self, signal_names):
        return [(signal_name, payload) for signal_name, payload in self.captured_signals if signal_name in signal_names]
