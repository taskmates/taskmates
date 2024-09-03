from typing import TypedDict

from taskmates.core.signal_receivers.current_markdown import CurrentMarkdown
from taskmates.core.signal_receivers.current_step import CurrentStep
from taskmates.core.signal_receivers.interrupted_or_killed_collector import InterruptedOrKilledCollector
from taskmates.core.signal_receivers.max_steps_manager import MaxStepsManager
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector


class SessionState(TypedDict):
    pass


class WorkflowState(TypedDict):
    interrupted_or_killed: InterruptedOrKilledCollector
    return_value: ReturnValueCollector
    max_steps_manager: MaxStepsManager
    current_step: CurrentStep
    current_markdown: CurrentMarkdown


class StepState(TypedDict):
    pass
