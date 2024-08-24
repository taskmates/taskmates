from abc import ABC, abstractmethod

from taskmates.types import Chat


class CompletionProvider(ABC):
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

    @abstractmethod
    async def perform_completion(self, chat: Chat):
        pass
