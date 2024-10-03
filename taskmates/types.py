from pathlib import Path
from typing import Dict, List, Union, MutableMapping

from typing_extensions import TypedDict, NotRequired, Literal


class Chat(TypedDict):
    markdown_chat: str
    completion_opts: 'CompletionOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


# TODO: maybe this should be a type of `inputs`
class CompletionOpts(TypedDict):
    model: NotRequired[str]
    max_steps: NotRequired[int]
    workflow: NotRequired[str]
    tools: NotRequired[dict]
    participants: NotRequired[dict]
    jupyter_enabled: NotRequired[bool]
    # TODO: move this to job context
    inputs: NotRequired[dict]


class CompletionPayload(TypedDict):
    type: str
    version: NotRequired[str]
    markdown_chat: str
    completion_context: 'CompletionContext'
    completion_opts: CompletionOpts


class MarkdownMessageSection(TypedDict):
    raw_content: str
    message_body: str
    role: str
    attributes: Dict[str, any]
    messages: NotRequired[List[Dict[str, Union[str, list[dict]]]]]


class CompletionContext(TypedDict):
    request_id: NotRequired[str]
    # TODO: should request_id, cwd and env be in the same place?
    # They don't seem to always share the same lifecycle
    # Example:
    # - request_id -> workflow
    # - markdown_path -> completion job
    # - cwd is more static -> completion job
    # - env is more dynamic -> step
    cwd: NotRequired[str]
    # TODO: move this to job context
    env: NotRequired[MutableMapping[str, str]]
    markdown_path: NotRequired[str]


class ClientConfig(TypedDict):
    endpoint: NotRequired[str]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    interactive: NotRequired[bool]
    taskmates_dirs: NotRequired[list[str | Path]]


class ServerConfig(TypedDict):
    pass


class StepContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]
    # TODO: move this to inputs
    current_step: NotRequired[int]


class JobContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]
