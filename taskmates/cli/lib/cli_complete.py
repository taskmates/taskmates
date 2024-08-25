from loguru import logger
from typeguard import typechecked

from taskmates.context_builders.build_cli_context import build_cli_context
from taskmates.core.chat_session import ChatSession
from taskmates.io.history_sink import HistorySink
from taskmates.io.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.sdk.extension_manager import EXTENSION_MANAGER
from taskmates.signals.signals import Signals


@typechecked
async def cli_complete(history: str | None,
                       incoming_messages: list[str], args):
    EXTENSION_MANAGER.get().initialize()

    handlers = [
        SigIntAndSigTermController(),
        StdoutCompletionStreamer(args.format),
        HistorySink(args.history)
    ]

    try:
        contexts = build_cli_context(args)
        with Signals().connected_to(handlers) as signals:
            result = await ChatSession(
                history=history,
                incoming_messages=incoming_messages,
                contexts=contexts,
                signals=signals
            ).resume()

        return result
    except Exception as e:
        await signals.response.error.send_async(e)
        logger.error(e)