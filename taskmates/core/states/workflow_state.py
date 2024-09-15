from typing import TypedDict

from taskmates.core.io.listeners.current_markdown import CurrentMarkdown
from taskmates.core.io.listeners.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.rules.max_steps_manager import MaxStepsManager
from taskmates.core.states.current_step import CurrentStep
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector


class WorkflowState(TypedDict):
    interrupted_or_killed: InterruptedOrKilled
    return_value: ReturnValueCollector
    max_steps_manager: MaxStepsManager
    current_step: CurrentStep
    current_markdown: CurrentMarkdown
