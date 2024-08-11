import contextvars
from typing import TypedDict

from taskmates.config.client_config import CLIENT_CONFIG, ClientConfig
from taskmates.config.completion_context import COMPLETION_CONTEXT, CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS, CompletionOpts
from taskmates.config.server_config import SERVER_CONFIG, ServerConfig


class Contexts(TypedDict):
    client_config: ClientConfig
    completion_context: CompletionContext
    completion_opts: CompletionOpts
    server_config: ServerConfig


defaults = {
    "client_config": CLIENT_CONFIG,
    "server_config": SERVER_CONFIG,
    "completion_context": COMPLETION_CONTEXT,
    "completion_opts": COMPLETION_OPTS,
}

CONTEXTS: contextvars.ContextVar['Contexts'] = contextvars.ContextVar('contexts', default=defaults)
