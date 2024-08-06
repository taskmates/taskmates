import contextvars
import os
from pathlib import Path

from typing_extensions import TypedDict


class ServerConfig(TypedDict):
    pass


SERVER_CONFIG: contextvars.ContextVar[ServerConfig] = contextvars.ContextVar(
    "ServerConfig",
    default={
    })
