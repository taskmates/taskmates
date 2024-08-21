import os
from uuid import uuid4

from taskmates.config.completion_opts import CompletionOpts
from taskmates.contexts import Contexts, build_default_contexts


def build_sdk_context(completion_opts: CompletionOpts) -> Contexts:
    contexts = build_default_contexts()
    request_id = str(uuid4())

    contexts["completion_context"].update({
        "request_id": request_id,
        "env": os.environ.copy(),
        "cwd": os.getcwd(),
    })

    contexts["completion_opts"].update(completion_opts.copy())

    contexts["client_config"].update({
        "interactive": True,
        "format": "completion",
    })

    return contexts
