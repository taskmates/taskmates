import contextvars
import os
from pathlib import Path

from typing_extensions import TypedDict, NotRequired

from taskmates.lib.root_path.root_path import root_path


class CompletionOpts(TypedDict):
    model: str
    template_params: NotRequired[dict]
    max_interactions: NotRequired[int]
    taskmates_dirs: NotRequired[list[str | Path]]
    # max_depth: int
    # max_hops: int


COMPLETION_OPTS: contextvars.ContextVar[CompletionOpts] = contextvars.ContextVar(
    "CompletionOpts",
    default={
        "model": 'claude-3-5-sonnet-20240620',
        "template_params": {},
        "max_interactions": 10000,  # Changed from float('inf') to a finite number
        "taskmates_dirs": [
            Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates"))),
            root_path() / "taskmates" / "default_config",
        ]
    })
