from abc import ABC, abstractmethod

from taskmates.config.completion_context import CompletionContext
from taskmates.contexts import Contexts
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class CompletionProvider(ABC):
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

    @abstractmethod
    async def perform_completion(self, chat: Chat, contexts: Contexts, signals: Signals):
        pass
