from pathlib import Path

from typing_extensions import TypedDict, NotRequired


class CompletionOpts(TypedDict):
    model: str
    template_params: NotRequired[dict]
    max_steps: NotRequired[int]
    taskmates_dirs: NotRequired[list[str | Path]]
