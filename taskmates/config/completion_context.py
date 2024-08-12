from typing import MutableMapping

from typing_extensions import TypedDict, NotRequired


class CompletionContext(TypedDict):
    request_id: NotRequired[str]
    cwd: NotRequired[str]
    env: NotRequired[MutableMapping[str, str]]
    markdown_path: NotRequired[str]

