import contextvars

from typing_extensions import TypedDict, NotRequired, Literal


class ClientConfig(TypedDict):
    endpoint: NotRequired[str]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    interactive: bool


CLIENT_CONFIG: contextvars.ContextVar[ClientConfig] = contextvars.ContextVar(
    "ClientConfig",
    default={
        "endpoint": None,
        "format": "completion",
        "output": None,
        "interactive": True,
    })
