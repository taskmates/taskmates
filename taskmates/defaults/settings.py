import os
from pathlib import Path
from uuid import uuid4

from taskmates import root_path
from taskmates.core.workflow_engine.run_context import RunContext

bundled_taskmates_dir = str(root_path() / "taskmates" / "defaults")
system_taskmates_dir = str(Path(os.environ.get("TASKMATES_HOME", str(Path.home() / ".taskmates"))))

default_taskmates_dirs = [
    system_taskmates_dir,
    bundled_taskmates_dir,
]


class Settings:
    @staticmethod
    def get() -> RunContext:
        request_id = str(uuid4())
        taskmates_env = os.environ.get("TASKMATES_ENV", "production")
        cwd = os.getcwd()

        local_taskmates_dir = str(Path(cwd) / ".taskmates")
        taskmates_dirs = [local_taskmates_dir] + default_taskmates_dirs

        if taskmates_env == "test":
            env_runner_environment = {
                "cwd": cwd,
                "env": {},
            }
            env_run_opts = {
                "model": 'quote',
                "max_steps": 2,
            }
        elif taskmates_env == "integration_test":
            env_runner_environment = {
                "cwd": cwd,
                "env": os.environ.copy(),
            }
            env_run_opts = {
                "model": 'claude-sonnet-4-5',
                "max_steps": 10,
            }
        else:
            env_runner_environment = {
                "env": os.environ.copy(),
            }
            env_run_opts = {
                "model": 'claude-sonnet-4-5',
                "max_steps": 10000,
            }

        return {
            "runner_environment": {
                **env_runner_environment,
                "request_id": request_id,
                "taskmates_dirs": taskmates_dirs,
                "markdown_path": "<function>",
            },
            "run_opts": {
                **env_run_opts
            }
        }
