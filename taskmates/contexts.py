import contextvars
import os
from pathlib import Path
from typing import TypedDict

from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.config.step_context import StepContext
from taskmates.lib.root_path.root_path import root_path


class Contexts(TypedDict):
    client_config: ClientConfig
    completion_context: CompletionContext
    completion_opts: CompletionOpts
    server_config: ServerConfig
    step_context: StepContext


bundled_taskmates_dir = root_path() / "taskmates" / "defaults"
system_taskmates_dir = Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates")))

default_taskmates_dirs = [
    system_taskmates_dir,
    bundled_taskmates_dir,
]

defaults = {
    "client_config": {},
    "server_config": {},
    "completion_context": {},
    "step_context": {
        "current_step": 0,
    },
    "completion_opts": {
        "model": 'claude-3-5-sonnet-20240620',
        "template_params": {},
        "max_steps": 10000,
        "taskmates_dirs": default_taskmates_dirs,
    },
}

CONTEXTS: contextvars.ContextVar['Contexts'] = contextvars.ContextVar('contexts', default=defaults)
