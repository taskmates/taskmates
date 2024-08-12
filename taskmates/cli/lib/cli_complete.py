from loguru import logger
from typeguard import typechecked

from taskmates.context_builders.build_cli_context import build_cli_context
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.history_sink import HistorySink
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.lib.context_.temp_context import temp_context
from taskmates.signals.signals import Signals, SIGNALS


@typechecked
async def cli_complete(history: str | None,
                       incoming_messages: list[str], args):
    handlers = [
        SigIntAndSigTermController(),
        StdoutCompletionStreamer(args.format),
        HistorySink(args.history)
    ]

    with temp_context(SIGNALS, Signals()) as signals, \
            signals.connected_to(handlers):
        try:
            with build_cli_context(args) as contexts:
                result = await CompletionEngine().perform_completion(
                    history,
                    incoming_messages,
                    contexts,
                    signals
                )
        except Exception as e:
            logger.error(e)

        return result
