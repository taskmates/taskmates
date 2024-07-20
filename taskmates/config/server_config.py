import contextvars
import os
from pathlib import Path

from typing_extensions import TypedDict


class ServerConfig(TypedDict):
    taskmates_dir: str


SERVER_CONFIG: contextvars.ContextVar[ServerConfig] = contextvars.ContextVar(
    "ServerConfig",
    default={
        "taskmates_dir": os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")),
    })
