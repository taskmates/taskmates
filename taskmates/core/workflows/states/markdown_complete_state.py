from typing import TypedDict

from taskmates.core.workflows.markdown_completion.max_steps_check import MaxStepsCheck
from taskmates.core.workflows.states.current_step import CurrentStep


class MarkdownCompleteState(TypedDict):
    max_steps_check: MaxStepsCheck
    current_step: CurrentStep
