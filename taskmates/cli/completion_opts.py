from typing import TypedDict, NotRequired, Literal

from taskmates.cli.completion_context import CompletionContext


class CompletionOpts(TypedDict):
    endpoint: NotRequired[str]
    format: NotRequired[Literal["full", "text", "completion"]]
    output: NotRequired[str]
    context: CompletionContext
