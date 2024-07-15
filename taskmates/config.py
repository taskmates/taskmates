import contextvars
import os
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar
from typing_extensions import TypedDict, NotRequired, Literal
from uuid import uuid4

T = TypeVar('T')


class ServerConfig(TypedDict):
    taskmates_dir: str


class CompletionContext(TypedDict):
    request_id: str
    cwd: str
    markdown_path: str


class ClientConfig(TypedDict):
    endpoint: NotRequired[str]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    interactive: bool


class CompletionOpts(TypedDict):
    model: str
    template_params: NotRequired[dict]
    max_interactions: NotRequired[int]
    # max_depth: int
    # max_hops: int


CLIENT_CONFIG: contextvars.ContextVar[ClientConfig] = contextvars.ContextVar(
    "ClientConfig",
    default={
        "endpoint": None,
        "format": "completion",
        "output": None,
        "interactive": True,
    })

COMPLETION_CONTEXT: contextvars.ContextVar[CompletionContext] = contextvars.ContextVar(
    "CompletionContext",
    default={
        "request_id": str(uuid4()),
        "markdown_path": str(Path(os.getcwd()) / f"{str(uuid4())}.md"),
        "cwd": os.getcwd()
    })

COMPLETION_OPTS: contextvars.ContextVar[CompletionOpts] = contextvars.ContextVar(
    "CompletionOpts",
    default={
        "model": 'claude-3-5-sonnet-20240620',
        "template_params": {},
        "max_interactions": 100,  # Changed from float('inf') to a finite number
    })

SERVER_CONFIG: contextvars.ContextVar[ServerConfig] = contextvars.ContextVar(
    "ServerConfig",
    default={
        "taskmates_dir": os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")),
    })


@contextmanager
def updated_config(var: contextvars.ContextVar[T], value: T):
    current_value = var.get()
    merged_value = {**current_value, **value}
    token = var.set(merged_value)
    try:
        yield merged_value
    finally:
        var.reset(token)
