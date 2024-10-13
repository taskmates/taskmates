from typing import TypedDict

from taskmates.workflows.rules.max_steps_check import MaxStepsCheck
from taskmates.workflows.states.current_step import CurrentStep


class MarkdownCompleteState(TypedDict):
    max_steps_check: MaxStepsCheck
    current_step: CurrentStep
