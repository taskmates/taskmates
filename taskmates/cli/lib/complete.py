import os
from contextlib import contextmanager
from typing import List, Optional
from uuid import uuid4

from typeguard import typechecked

from taskmates.cli.lib.handler import Handler
from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import COMPLETION_CONTEXT, CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS
from taskmates.config.server_config import SERVER_CONFIG
from taskmates.config.updated_config import updated_config
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.signals.signals import Signals, SIGNALS


@typechecked
@contextmanager
def build_context(args):
    request_id = str(uuid4())
    completion_context: CompletionContext = {
        "request_id": request_id,
        "markdown_path": str(os.path.join(os.getcwd(), f"{request_id}.md")),
        "cwd": os.getcwd(),
    }
    client_config = ClientConfig(interactive=False,
                                 format=args.format,
                                 endpoint=args.endpoint)
    completion_opts = {
        "model": args.model,
        "template_params": merge_template_params(args.template_params),
        "max_interactions": args.max_interactions,
    }

    with updated_config(COMPLETION_CONTEXT, completion_context), \
            updated_config(COMPLETION_OPTS, completion_opts):
        yield {
            'context': COMPLETION_CONTEXT.get(),
            'client_config': client_config,
            'server_config': SERVER_CONFIG.get(),
            'completion_opts': COMPLETION_OPTS.get()
        }


@typechecked
async def complete(markdown: str, args, handlers: Optional[List[Handler]] = None):
    if handlers is None:
        handlers = [StdoutCompletionStreamer(args.format),
                    SigIntAndSigTermController()]

    signals = Signals()
    SIGNALS.set(signals)

    # Connect handlers
    for handler in handlers:
        handler.connect(signals)

    try:
        with build_context(args) as config:
            result = await CompletionEngine().perform_completion(
                config['context'],
                markdown,
                config['server_config'],
                config['client_config'],
                config['completion_opts'],
                signals
            )
    finally:
        # Disconnect handlers
        for handler in handlers:
            handler.disconnect(signals)

    return result
