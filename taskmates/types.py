from typing import TypedDict, NotRequired, Dict, List, Union

from taskmates.config.completion_context import CompletionContext


class Chat(TypedDict):
    markdown_chat: str
    completion_opts: 'CompletionOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


class CompletionOpts(TypedDict):
    model: NotRequired[str]
    max_steps: NotRequired[int]
    tools: NotRequired[dict]
    participants: NotRequired[dict]
    jupyter_enabled: NotRequired[bool]
    template_params: NotRequired[dict]


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
