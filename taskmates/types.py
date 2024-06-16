from typing import TypedDict, NotRequired

from taskmates.config import CompletionContext, CompletionOpts


class Chat(TypedDict):
    metadata: 'MarkdownOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


class MarkdownOpts(TypedDict):
    model: NotRequired[str]
    tools: NotRequired[dict]
    participants: NotRequired[dict]
    jupyter_enabled: NotRequired[bool]


class CompletionPayload(TypedDict):
    type: str
    markdown_chat: str
    completion_context: CompletionContext
    completion_opts: CompletionOpts
