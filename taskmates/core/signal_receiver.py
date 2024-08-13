from abc import ABC, abstractmethod

from taskmates.signals.signals import Signals


class SignalReceiver(ABC):
    @abstractmethod
    def connect(self, signals: Signals):
        pass

    @abstractmethod
    def disconnect(self, signals: Signals):
        pass
