import os
from contextlib import contextmanager
from uuid import uuid4

from taskmates.config.completion_opts import CompletionOpts
from taskmates.contexts import CONTEXTS, Contexts
from taskmates.lib.context_.context_fork import context_fork
from taskmates.sdk.extension_manager import EXTENSION_MANAGER


@contextmanager
def build_sdk_context(completion_opts: CompletionOpts) -> Contexts:
    with context_fork(CONTEXTS) as contexts:
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

        EXTENSION_MANAGER.get().after_build_contexts(contexts)

        yield contexts
