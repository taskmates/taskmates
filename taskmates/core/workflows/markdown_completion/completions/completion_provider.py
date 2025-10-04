from abc import ABC, abstractmethod

from typeguard import typechecked

from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import ChatCompletionRequest


@typechecked
class CompletionProvider(ABC):
    @abstractmethod
    def can_complete(self, chat: ChatCompletionRequest):
        raise NotImplemented

    @abstractmethod
    async def perform_completion(
            self,
            chat: ChatCompletionRequest,
            control_signals: ControlSignals,
            execution_environment_signals: ExecutionEnvironmentSignals,
            status_signals: StatusSignals
    ):
        raise NotImplemented


