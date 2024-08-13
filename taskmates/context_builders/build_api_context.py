import os
from contextlib import contextmanager
from uuid import uuid4

from taskmates.contexts import CONTEXTS, Contexts
from taskmates.lib.context_.context_fork import context_fork
from taskmates.sdk.extension_manager import EXTENSION_MANAGER
from taskmates.types import CompletionPayload


@contextmanager
def build_api_context(payload: CompletionPayload) -> Contexts:
    with context_fork(CONTEXTS) as contexts:
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

        EXTENSION_MANAGER.get().after_build_contexts(contexts)

        yield contexts
