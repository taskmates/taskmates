from pathlib import Path
from typing import MutableMapping

from typing_extensions import TypedDict, NotRequired, Literal


class Chat(TypedDict):
    markdown_chat: str
    run_opts: 'RunOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


class ApiRequest(TypedDict):
    type: str
    version: NotRequired[str]
    markdown_chat: str
    runner_environment: 'RunnerEnvironment'
    run_opts: 'RunOpts'


class RunOpts(TypedDict):
    model: NotRequired[str]
    workflow: NotRequired[str]
    tools: NotRequired[dict]
    participants: NotRequired[dict]
    inputs: NotRequired[dict]

    max_steps: NotRequired[int]
    jupyter_enabled: NotRequired[bool]


class RunnerConfig(TypedDict):
    endpoint: NotRequired[str]
    interactive: NotRequired[bool]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    taskmates_dirs: NotRequired[list[str | Path]]


class RunnerEnvironment(TypedDict):
    request_id: NotRequired[str]
    markdown_path: NotRequired[str]
    cwd: NotRequired[str]
    env: NotRequired[MutableMapping[str, str]]


# TODO: move out

class StepContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]
    # TODO: move this to inputs
    current_step: NotRequired[int]


class JobContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]
