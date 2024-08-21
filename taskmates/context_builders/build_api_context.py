import os
from uuid import uuid4

from taskmates.contexts import Contexts, build_default_contexts
from taskmates.types import CompletionPayload


def build_api_context(payload: CompletionPayload) -> Contexts:
    contexts = build_default_contexts()
    request_id = str(uuid4())

    contexts["completion_context"].update(payload["completion_context"].copy())
    contexts["completion_context"].update({
        "request_id": request_id,
        "env": os.environ.copy(),
    })

    contexts["completion_opts"].update(payload["completion_opts"].copy())

    contexts["client_config"].update({
        "interactive": True,
        "format": "completion",
    })

    return contexts
