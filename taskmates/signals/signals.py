import contextvars
from contextlib import contextmanager
from typing import List

from taskmates.signals.base_signals import ControlSignals, OutputSignals, LifecycleSignals


class Signals:
    def __init__(self):
        self.control = ControlSignals()
        self.lifecycle = LifecycleSignals()
        self.output = OutputSignals()

    @contextmanager
    def connected_to(self, objs: List):
        try:
            for obj in objs:
                obj.connect(self)
            yield
        finally:
            for obj in objs:
                obj.disconnect(self)


SIGNALS: contextvars.ContextVar['Signals'] = contextvars.ContextVar('signals')
