import contextvars
import os
from pathlib import Path
from typing import TypedDict, NotRequired
from uuid import uuid4


class CompletionContext(TypedDict):
    # propagates
    request_id: str
    cwd: str
    template_params: dict

    interactive: bool

    # max_depth: int
    # max_hops: int
    taskmates_dir: str

    # local
    markdown_path: str
    max_interactions: NotRequired[int]
    model: str


CompletionContextDefaults: contextvars.ContextVar[CompletionContext] = contextvars.ContextVar(
    "CompletionContextDefaults",
    default=CompletionContext(**{
        "request_id": str(uuid4()),
        "markdown_path": str(Path(os.getcwd()) / f"{str(uuid4())}.md"),
        "taskmates_dir": os.environ.get("TASKMATES_PATH", "/var/tmp/taskmates"),
        "model": 'claude-3-opus-20240229',
        "cwd": os.getcwd(),
        "template_params": {},
        "interactive": False,
    }))
