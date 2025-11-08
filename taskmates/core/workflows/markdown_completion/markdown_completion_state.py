from typing import TypedDict

from typeguard import typechecked

from taskmates.core.workflows.markdown_completion.max_steps_check import MaxStepsCheck
from taskmates.core.workflows.states.current_step import CurrentStep
from taskmates.core.workflows.states.markdown_chat import MarkdownChat


@typechecked
class MarkdownCompletionState:
    class State(TypedDict):
        markdown_chat: MarkdownChat
        current_step: CurrentStep
        max_steps_check: MaxStepsCheck

    def __init__(self, inputs: dict, max_steps: int):
        markdown_chat = inputs.get('markdown_chat')
        if not markdown_chat:
            raise ValueError("markdown_chat must be provided in inputs")

        current_step = CurrentStep()
        self.state: MarkdownCompletionState.State = {
            "markdown_chat": MarkdownChat(),
            "current_step": current_step,
            "max_steps_check": MaxStepsCheck(current_step, max_steps),
        }

        if markdown_chat:
            self.state["markdown_chat"].append_to_format("full", markdown_chat)
