from typing import TypedDict, NotRequired

from nbformat import NotebookNode

from taskmates.config import CompletionContext, CompletionOpts


class Chat(TypedDict):
    metadata: 'MarkdownOpts'
    messages: list[dict]
    participants: list[str]
    available_tools: list[str]
    last_message: 'LastMessage'


class LastMessage(TypedDict):
    recipient: str | None
    recipient_role: str | None
    code_cells: list[NotebookNode]


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
