import contextvars

from taskmates.signals.base_signals import ControlSignals, OutputSignals


class Signals:
    def __init__(self):
        self.control = ControlSignals()
        self.output = OutputSignals()


SIGNALS: contextvars.ContextVar['Signals'] = contextvars.ContextVar('signals')
