from typing import MutableMapping

from typing_extensions import TypedDict, NotRequired


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
    env: NotRequired[MutableMapping[str, str]]
    markdown_path: NotRequired[str]

