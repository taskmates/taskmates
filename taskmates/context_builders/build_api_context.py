import os
from uuid import uuid4

from taskmates.context_builders.build_default_context import build_default_contexts
from taskmates.contexts import Contexts
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

    contexts["client_config"].update(dict(interactive=True,
                                          format="completion"))

    return contexts
