import contextvars
from typing import TypedDict, NotRequired, Literal

from taskmates.assistances.completion_context import CompletionContext, CompletionContextDefaults


class CompletionOpts(TypedDict):
    # backend / propagates
    endpoint: NotRequired[str]

    # cli / local
    format: NotRequired[Literal["full", "text", "completion"]]

    # calculated
    output: NotRequired[str]

    # ---
    context: CompletionContext


CompletionOptsDefaults: contextvars.ContextVar[CompletionOpts] = contextvars.ContextVar("CompletionOptsDefaults", default=CompletionOpts(
    format='text',
    context=CompletionContextDefaults.get()
))
