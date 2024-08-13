from typing_extensions import TypedDict, NotRequired


class StepContext(TypedDict):
    current_step: NotRequired[int]
