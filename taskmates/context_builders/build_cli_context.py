import os
from uuid import uuid4

from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.contexts import Contexts
from taskmates.context_builders.build_default_context import build_default_contexts


def build_cli_context(args) -> Contexts:
    contexts = build_default_contexts()
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
        "model": args.model if "model" in args else None,
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

    return contexts
