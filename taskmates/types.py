from typing import TypedDict, NotRequired, Dict, List, Union

from taskmates.config import CompletionContext, CompletionOpts


class Chat(TypedDict):
    metadata: 'MarkdownOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


class MarkdownOpts(TypedDict):
    model: NotRequired[str]
    max_interactions: NotRequired[int]
    tools: NotRequired[dict]
    participants: NotRequired[dict]
    jupyter_enabled: NotRequired[bool]


class CompletionPayload(TypedDict):
    type: str
    version: NotRequired[str]
    markdown_chat: str
    completion_context: CompletionContext
    completion_opts: CompletionOpts


class MarkdownMessageSection(TypedDict):
    raw_content: str
    message_body: str
    role: str
    attributes: Dict[str, any]
    messages: NotRequired[List[Dict[str, Union[str, list[dict]]]]]
