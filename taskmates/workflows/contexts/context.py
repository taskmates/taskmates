import os
from pathlib import Path

from typing_extensions import TypedDict

from taskmates.lib.root_path.root_path import root_path
from taskmates.types import RunOpts, RunnerEnvironment, RunnerConfig


class Context(TypedDict):
    runner_config: RunnerConfig
    runner_environment: RunnerEnvironment
    run_opts: RunOpts


bundled_taskmates_dir = str(root_path() / "taskmates" / "defaults")
system_taskmates_dir = str(Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates"))))

default_taskmates_dirs = [
    system_taskmates_dir,
    bundled_taskmates_dir,
]
