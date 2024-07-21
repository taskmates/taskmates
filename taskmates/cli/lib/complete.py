import asyncio
import os
import signal
from pathlib import Path
from uuid import uuid4

from typeguard import typechecked

from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS
from taskmates.config.server_config import ServerConfig, SERVER_CONFIG
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.output_signals_to_websocket_bridge import OutputSignalsToWebsocketBridge
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.io.websocket_to_control_signals_bridge import WebsocketToControlSignalsBridge
from taskmates.signal_config import SignalConfig, SignalMethod
from taskmates.signals.signals import Signals, SIGNALS

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
            await signals.control.interrupt_request.send_async({})
            await asyncio.sleep(5)
            received_signal = None
        elif received_signal == signal.SIGTERM:
            await signals.control.kill.send_async({})
            await asyncio.sleep(5)
            break
        await asyncio.sleep(0.1)


@typechecked
async def complete(markdown: str,
                   args,
                   signal_config: SignalConfig):
    request_id = str(uuid4())

    # If --output is not provided, write to request_id file in /var/tmp
    # output = args.output or f"~/.taskmates/completions/{request_id}.md"
    # Path(output).parent.mkdir(parents=True, exist_ok=True)

    context: CompletionContext = {
        "request_id": request_id,
        "markdown_path": str(Path(os.getcwd()) / f"{request_id}.md"),
        "cwd": os.getcwd(),
    }

    server_config: ServerConfig = SERVER_CONFIG.get()

    client_config = ClientConfig(interactive=False,
                                 format=args.format,
                                 endpoint=args.endpoint,
                                 # output=(output if args.output else None)
                                 )

    completion_opts = {
        "model": args.model,
        "template_params": merge_template_params(args.template_params),
        "max_interactions": args.max_interactions,
    }

    COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})

    signals = Signals()
    SIGNALS.set(signals)

    input_bridge = None
    output_bridge = None

    if signal_config.input_method == SignalMethod.WEBSOCKET:
        input_bridge = WebsocketToControlSignalsBridge(signals.control, signal_config.websocket_url)
        await input_bridge.connect()

    if signal_config.output_method == SignalMethod.WEBSOCKET:
        output_bridge = OutputSignalsToWebsocketBridge(signals.response, signal_config.websocket_url)
        await output_bridge.connect()

    format = client_config.get('format', 'text')
    StdoutCompletionStreamer(format).connect(signals)

    async def process_return_value(status):
        if status['result']:
            pass
        else:
            print(status['summary'], flush=True)
            # noinspection PyUnresolvedReferences,PyProtectedMember
            os._exit(-1)

    signals.output.return_value.connect(process_return_value, weak=False)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    process_task = asyncio.create_task(CompletionEngine().perform_completion(
        context,
        markdown,
        server_config,
        client_config,
        completion_opts,
        signals))
    signal_task = asyncio.create_task(handle_signals(signals))

    try:
        done, pending = await asyncio.wait(
            [process_task, signal_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
    finally:
        if input_bridge:
            await input_bridge.close()
        if output_bridge:
            await output_bridge.close()


def merge_template_params(template_params: list) -> dict:
    merged = {}
    for params in template_params:
        merged.update(params)
    return merged
