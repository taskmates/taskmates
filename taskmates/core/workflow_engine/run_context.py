from typing_extensions import TypedDict

from taskmates.types import RunOpts, RunnerEnvironment


class RunContext(TypedDict):
    runner_environment: RunnerEnvironment
    run_opts: RunOpts
