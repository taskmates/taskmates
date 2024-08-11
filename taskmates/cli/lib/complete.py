from typing import List, Optional

from loguru import logger
from typeguard import typechecked

from taskmates.cli.lib.build_context import build_context
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.history_sink import HistorySink
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.signals.handler import Handler
from taskmates.signals.signals import Signals, SIGNALS


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
                config['completion_context'],
                history,
                incoming_messages,
                config['server_config'],
                config['client_config'],
                config['completion_opts'],
                signals
            )
    except Exception as e:
        logger.error(e)
    finally:
        # Disconnect handlers
        for handler in handlers:
            handler.disconnect(signals)

    return result
