import functools
from contextlib import contextmanager
from typing import List

from blinker import Namespace, Signal


def relay(self_signals, other_signals):
    for signal_group_name, signal_group in vars(other_signals).items():
        if isinstance(signal_group, BaseSignals):
            for signal_name, other_signal in signal_group.namespace.items():
                self_signal = self_signals.__getattribute__(signal_name)
                self_signal.connect(functools.partial(other_signal, signal_name), weak=False)
                # other_signal.connect(functools.partial(self_signal, signal_name), weak=False)


def disconnect_relay(self_signals, other_signals):
    for signal_group_name, signal_group in vars(other_signals).items():
        if isinstance(signal_group, BaseSignals):
            for signal_name, other_signal in signal_group.namespace.items():
                self_signal = self_signals.__getattribute__(signal_name)
                self_signal.disconnect(other_signal)
                # other_signal.disconnect(self_signal)


@contextmanager
def connected_signals(this_signals: list['BaseSignals'], other_signals: list['BaseSignals']):
    relay(this_signals, other_signals)
    try:
        yield
    finally:
        disconnect_relay(this_signals, other_signals)


class BaseSignals:
    def __init__(self):
        self.namespace = Namespace()

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()

    @contextmanager
    def connected_to(self, objs: List[Signal], handler: callable):
        try:
            for obj in objs:
                obj.connect(handler)
            yield self
        finally:
            for obj in objs:
                obj.disconnect(handler)

    def connect_all(self, signals: 'BaseSignals'):
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.connect(
                        functools.partial(self.__getattribute__(signal_name), signal_name),
                        weak=False
                    )

    def disconnect_all(self, signals: 'BaseSignals'):
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.disconnect(self.__getattribute__(signal_name))
