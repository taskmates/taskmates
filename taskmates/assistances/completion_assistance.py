from abc import ABC, abstractmethod

from taskmates.signals import Signals


class CompletionAssistance(ABC):
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def can_complete(self, chat):
        pass

    @abstractmethod
    async def perform_completion(self, context: dict, chat: dict, signals: Signals):
        pass
