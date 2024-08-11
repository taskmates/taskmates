import contextvars
import os
from pathlib import Path
from typing import MutableMapping
from uuid import uuid4

from typing_extensions import TypedDict


class CompletionContext(TypedDict):
    request_id: str
    cwd: str
    env: MutableMapping[str, str]
    markdown_path: str


COMPLETION_CONTEXT: contextvars.ContextVar[CompletionContext] = contextvars.ContextVar(
    "CompletionContext",
    default={
        "request_id": str(uuid4()),
        "markdown_path": str(Path(os.getcwd()) / f"{str(uuid4())}.md"),
        "cwd": os.getcwd(),
        "env": os.environ.copy(),
    })
