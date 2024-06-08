import asyncio
import os
import signal

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionContext, ClientConfig
from taskmates.signals import Signals, SIGNALS

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
            await signals.interrupt.send_async({})
            await asyncio.sleep(5)
            received_signal = None
        elif received_signal == signal.SIGTERM:
            await signals.kill.send_async({})
            await asyncio.sleep(5)
            break
        await asyncio.sleep(0.1)


async def perform_direct_completion(markdown,
                                    context: CompletionContext,
                                    client_config: ClientConfig):
    signals = Signals()
    SIGNALS.set(signals)

    completion_chunks = []

    async def process_chunk(chunk):
        print(chunk, end="", flush=True)

    async def process_response_chunk(chunk):
        completion_chunks.append(chunk)

    if client_config.get('format') == 'full':
        signals.request.connect(process_chunk)
        signals.formatting.connect(process_chunk)
        signals.responder.connect(process_chunk)
    if client_config.get('format') == 'completion':
        signals.responder.connect(process_chunk)

    signals.response.connect(process_response_chunk)

    signals.response.connect(process_chunk)
    signals.error.connect(process_chunk)

    async def process_return_status(status):
        if status['result']:
            pass
        else:
            print(status['summary'], flush=True)
            # noinspection PyUnresolvedReferences,PyProtectedMember
            os._exit(-1)

    signals.return_status.connect(process_return_status)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    process_task = asyncio.create_task(MarkdownCompletionAssistance().perform_completion(context, markdown, signals))
    signal_task = asyncio.create_task(handle_signals(signals))

    done, pending = await asyncio.wait(
        [process_task, signal_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    return "".join(completion_chunks)
