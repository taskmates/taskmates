import os
from contextlib import contextmanager
from typing import List, Optional
from uuid import uuid4

from typeguard import typechecked

from taskmates.cli.lib.merge_template_params import merge_template_params
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.updated_config import updated_config
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.history_sink import HistorySink
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.signals.handler import Handler
from taskmates.signals.signals import Signals, SIGNALS
from taskmates.contexts import Contexts


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

    with updated_config(Contexts.completion_context, completion_context), \
            updated_config(Contexts.completion_opts, completion_opts):
        yield {
            'context': Contexts.completion_context.get(),
            'client_config': client_config,
            'server_config': Contexts.server_config.get(),
            'completion_opts': Contexts.completion_opts.get()
        }


@typechecked
async def complete(history: str | None, incoming_messages: list[str], args, handlers: Optional[List[Handler]] = None):
    if handlers is None:
        handlers = [
            SigIntAndSigTermController(),
            StdoutCompletionStreamer(args.format),
            HistorySink(args.history)
        ]

    signals = Signals()
    SIGNALS.set(signals)

    # Connect handlers
    for handler in handlers:
        handler.connect(signals)

    try:
        with build_context(args) as config:
            result = await CompletionEngine().perform_completion(
                config['context'],
                history,
                incoming_messages,
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
