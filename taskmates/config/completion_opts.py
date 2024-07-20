import contextvars

from typing_extensions import TypedDict, NotRequired


class CompletionOpts(TypedDict):
    model: str
    template_params: NotRequired[dict]
    max_interactions: NotRequired[int]
    # max_depth: int
    # max_hops: int


COMPLETION_OPTS: contextvars.ContextVar[CompletionOpts] = contextvars.ContextVar(
    "CompletionOpts",
    default={
        "model": 'claude-3-5-sonnet-20240620',
        "template_params": {},
        "max_interactions": 10000,  # Changed from float('inf') to a finite number
    })
