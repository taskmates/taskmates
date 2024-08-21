from uuid import uuid4

from taskmates.contexts import Contexts, build_default_contexts


def build_test_context(tmp_path) -> Contexts:
    contexts = build_default_contexts()
    request_id = str(uuid4())

    contexts["completion_context"].update({
        "request_id": request_id,
        "cwd": str(tmp_path),
        "env": {},
        "markdown_path": str(tmp_path / "chat.md")
    })

    contexts["completion_opts"].update({
        "model": "quote",
        "template_params": {},
        "max_steps": 1,
    })

    contexts["client_config"].update({
        "interactive": False,
    })

    return contexts
