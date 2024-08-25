from pathlib import Path

from typing_extensions import TypedDict, NotRequired, Literal


class ClientConfig(TypedDict):
    endpoint: NotRequired[str]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    interactive: NotRequired[bool]
    taskmates_dirs: NotRequired[list[str | Path]]
