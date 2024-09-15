import contextvars
import os
from pathlib import Path

from typing_extensions import TypedDict

from taskmates.lib.root_path.root_path import root_path
from taskmates.types import CompletionOpts, CompletionContext, ClientConfig, ServerConfig, StepContext, JobContext


class Contexts(TypedDict):
    client_config: ClientConfig
    completion_context: CompletionContext
    completion_opts: CompletionOpts
    server_config: ServerConfig
    step_context: StepContext
    job_context: JobContext


bundled_taskmates_dir = str(root_path() / "taskmates" / "defaults")
system_taskmates_dir = str(Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates"))))

default_taskmates_dirs = [
    system_taskmates_dir,
    bundled_taskmates_dir,
]

