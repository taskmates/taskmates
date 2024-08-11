import os
from pathlib import Path

from typing_extensions import TypedDict, NotRequired

from taskmates.lib.root_path.root_path import root_path


class CompletionOpts(TypedDict):
    model: str
    template_params: NotRequired[dict]
    max_steps: NotRequired[int]
    taskmates_dirs: NotRequired[list[str | Path]]
    # max_depth: int
    # max_hops: int


COMPLETION_OPTS: CompletionOpts = {
    "model": 'claude-3-5-sonnet-20240620',
    "template_params": {},
    "max_steps": 10000,  # Changed from float('inf') to a finite number
    "taskmates_dirs": [
        Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates"))),
        root_path() / "taskmates" / "default_config",
    ]
}
