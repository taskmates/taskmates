import os
from pathlib import Path
from typing import MutableMapping
from uuid import uuid4

from typing_extensions import TypedDict, NotRequired


class CompletionContext(TypedDict):
    request_id: NotRequired[str]
    cwd: str
    env: MutableMapping[str, str]
    markdown_path: str


COMPLETION_CONTEXT: CompletionContext = {
    "markdown_path": str(Path(os.getcwd()) / f"{str(uuid4())}.md"),
    "cwd": os.getcwd(),
    "env": os.environ.copy(),
}
