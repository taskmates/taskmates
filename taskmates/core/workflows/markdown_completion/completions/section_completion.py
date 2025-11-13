from abc import ABC, abstractmethod

from typeguard import typechecked

from taskmates.types import CompletionRequest


@typechecked
class SectionCompletion(ABC):
    @abstractmethod
    def can_complete(self, chat: CompletionRequest):
        raise NotImplemented

    @abstractmethod
    async def perform_completion(self, chat: CompletionRequest) -> str:
        raise NotImplemented
