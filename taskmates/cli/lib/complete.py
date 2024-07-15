import asyncio
import os
import signal

from typeguard import typechecked

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionContext, ClientConfig, CompletionOpts
from taskmates.signals import Signals, SIGNALS
from taskmates.sinks.websocket_signal_bridge import WebsocketSignalBridge

# Global variable to store the received signal
received_signal = None


# noinspection PyUnusedLocal
def signal_handler(sig, frame):
    global received_signal
    received_signal = sig


async def handle_signals(signals):
    global received_signal
    while True:
        if received_signal == signal.SIGINT:
            print(flush=True)
            print("Interrupting...", flush=True)
            print("Press Ctrl+C again to kill", flush=True)
            await signals.interrupt_request.send_async({})
            await asyncio.sleep(5)
            received_signal = None
        elif received_signal == signal.SIGTERM:
            await signals.kill.send_async({})
            await asyncio.sleep(5)
            break
        await asyncio.sleep(0.1)


@typechecked
async def complete(markdown: str,
                   context: CompletionContext,
                   client_config: ClientConfig,
                   completion_opts: CompletionOpts,
                   signals: Signals | None = None,
                   endpoint: str | None = None):
    if endpoint:
        # Use WebsocketSignalBridge when an endpoint is provided
        signal_bridge = WebsocketSignalBridge(
            endpoint=endpoint,
            completion_context=context,
            completion_opts=completion_opts,
            markdown_chat=markdown
        )
        signals = Signals()
        SIGNALS.set(signals)
        await signal_bridge.connect(signals)
    elif signals is None:
        signals = SIGNALS.get(None)
        if signals is None:
            signals = Signals()
            SIGNALS.set(signals)

    async def process_chunk(chunk):
        print(chunk, end="", flush=True)

    if client_config.get('format') == 'full':
        signals.request.connect(process_chunk, weak=False)
        signals.formatting.connect(process_chunk, weak=False)
        signals.responder.connect(process_chunk, weak=False)
        signals.response.connect(process_chunk, weak=False)
        signals.error.connect(process_chunk, weak=False)

    elif client_config.get('format') == 'original':
        signals.request.connect(process_chunk, weak=False)

    elif client_config.get('format') == 'completion':
        signals.responder.connect(process_chunk, weak=False)
        signals.response.connect(process_chunk, weak=False)
        signals.error.connect(process_chunk, weak=False)

    elif client_config.get('format') == 'text':
        signals.response.connect(process_chunk, weak=False)
    else:
        raise ValueError(f"Invalid format: {client_config.get('format')}")

    async def process_return_value(status):
        if status['result']:
            pass
        else:
            print(status['summary'], flush=True)
            # noinspection PyUnresolvedReferences,PyProtectedMember
            os._exit(-1)

    signals.return_value.connect(process_return_value, weak=False)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    process_task = asyncio.create_task(MarkdownCompletionAssistance().perform_completion(context, markdown, signals))
    signal_task = asyncio.create_task(handle_signals(signals))

    try:
        done, pending = await asyncio.wait(
            [process_task, signal_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
    finally:
        if endpoint:
            await signal_bridge.close()
