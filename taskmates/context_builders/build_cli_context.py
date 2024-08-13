import os
from contextlib import contextmanager
from uuid import uuid4

from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.contexts import CONTEXTS, Contexts
from taskmates.lib.context_.context_fork import context_fork
from taskmates.sdk.extension_manager import EXTENSION_MANAGER


@contextmanager
def build_cli_context(args) -> Contexts:
    with context_fork(CONTEXTS) as contexts:
        request_id = str(uuid4())

        # TODO: review this. these are unrelated
        # "request_id" -> execution context
        # "markdown_path" -> client context
        # "cwd" -> runtime context
        # "env" -> runtime context
        contexts["completion_context"].update({
            "request_id": request_id,
            "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
            "cwd": os.getcwd(),
            "env": os.environ.copy(),
        })

        contexts["completion_opts"].update({
            "model": args.model,
            "template_params": merge_template_params(args.template_params),
            "max_steps": args.max_steps,
        })

        # TODO separate config from options
        # endpoint is an option
        # maybe we should have an
        # EngineConfig + ClientParams or something like that
        contexts["client_config"].update({
            "interactive": False,
            "format": args.format,
            "endpoint": args.endpoint
        })

        EXTENSION_MANAGER.get().after_build_contexts(contexts)

        yield contexts
