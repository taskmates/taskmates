import os
from contextlib import contextmanager
from uuid import uuid4

from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.config.context_fork import context_fork
from taskmates.contexts import CONTEXTS, Contexts


@contextmanager
def build_context(args) -> Contexts:
    with context_fork(CONTEXTS) as contexts:
        request_id = str(uuid4())

        contexts["completion_context"].update({
            "request_id": request_id,
            "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
            "cwd": os.getcwd(),
            "env": os.environ.copy(),
        })

        contexts["completion_opts"].update({
            "model": args.model,
            "template_params": merge_template_params(args.template_params),
            "max_interactions": args.max_interactions,
        })

        contexts["client_config"].update({
            "interactive": False,
            "format": args.format,
            "endpoint": args.endpoint
        })

        yield contexts
