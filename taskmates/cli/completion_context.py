from typing import TypedDict


class CompletionContext(TypedDict):
    request_id: str
    markdown_path: str
    taskmates_dir: str
    model: str
    cwd: str
    template_params: dict
    interactive: bool
    max_interactions: int
