import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from taskmates.config.completion_opts import COMPLETION_OPTS
from taskmates.lib.context_.context_fork import context_fork
from taskmates.contexts import CONTEXTS, Contexts
from taskmates.types import CompletionPayload


@contextmanager
def build_context(payload: CompletionPayload) -> Contexts:
    with context_fork(CONTEXTS) as contexts:
        request_id = str(uuid4())

        contexts["completion_context"].update(payload["completion_context"].copy())
        contexts["completion_context"].update({
            "request_id": request_id,
            "env": os.environ.copy(),
        })

        contexts["completion_opts"].update(payload["completion_opts"].copy())

        # TODO: review this
        contexts["completion_opts"]["taskmates_dirs"] = [str(Path(payload["completion_context"]["cwd"]) / ".taskmates"),
                                                         *contexts["completion_opts"].get("taskmates_dirs",
                                                                                          COMPLETION_OPTS[
                                                                                              "taskmates_dirs"])]

        contexts["completion_opts"].setdefault("template_params", {})

        contexts["client_config"].update({
            "interactive": True,
            "format": "completion",
        })

        yield contexts
