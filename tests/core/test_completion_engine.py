import functools
import io
from typing import Any

import pytest

from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.history_sink import HistorySink
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.signals.handler import Handler
from taskmates.signals.signals import BaseSignals
from taskmates.signals.signals import Signals


class SignalCaptureHandler(Handler):
    def __init__(self):
        self.captured_signals: list[tuple[str, Any]] = []

    async def handle(self, signal_name: str, payload):
        self.captured_signals.append((signal_name, payload))

    async def signal_handler(self, signal_name: str, payload):
        await self.handle(signal_name, payload)

    def connect(self, signals):
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.connect(
                        functools.partial(self.signal_handler, signal_name),
                        weak=False
                    )

    def disconnect(self, signals):
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.disconnect(self.signal_handler)

    def filter_signals(self, signal_names):
        return [(signal_name, payload) for signal_name, payload in self.captured_signals if signal_name in signal_names]


@pytest.mark.asyncio
async def test_completion_engine_history(tmp_path):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    signal_capture = SignalCaptureHandler()
    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    history_sink = HistorySink(history_file)

    context: CompletionContext = {
        "request_id": "test_request_id",
        "cwd": str(tmp_path),
        "markdown_path": str(tmp_path / "test.md"),
    }
    server_config = ServerConfig()
    client_config = ClientConfig(interactive=False, endpoint="local")
    completion_opts = CompletionOpts(model="quote", template_params={}, taskmates_dirs=[])

    engine = CompletionEngine()
    signals = Signals()

    with signals.connected_to([signal_capture, history_sink]):
        await engine.perform_completion(
            context,
            history,
            incoming_messages,
            server_config,
            client_config,
            completion_opts,
            signals
        )

    interesting_signals = ['history', 'incoming_message', 'input_formatting', 'error']
    filtered_signals = signal_capture.filter_signals(interesting_signals)

    with open(history_file, "r") as f:
        history_content = f.read()

    print(f"Filtered signals: {filtered_signals}")
    print(f"History content: {history_content}")

    assert filtered_signals == [('history', 'Initial history\n'),
                                ('input_formatting', '\n'),
                                ('incoming_message', 'Incoming message'),
                                ('input_formatting', '\n\n')]
    assert history_content == "Initial history\n\nIncoming message\n\n**assistant>** \n> Initial history\n> \n> Incoming message\n> \n> \n\n"


@pytest.mark.asyncio
async def test_completion_engine_stdout_streamer(tmp_path):
    context: CompletionContext = {
        "request_id": "test_request_id",
        "cwd": "/tmp",
        "markdown_path": "/tmp/test.md",
    }
    server_config = ServerConfig()
    completion_opts = CompletionOpts(model="quote", template_params={}, taskmates_dirs=[])

    engine = CompletionEngine()

    text_output = io.StringIO()
    full_output = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    print("Testing 'text' format")  # Debug print
    text_signal_capture = SignalCaptureHandler()
    # Test with 'text' format
    with Signals().connected_to([
        text_signal_capture,
        StdoutCompletionStreamer('text', text_output)
    ]) as signals:
        client_config = ClientConfig(interactive=False, format='text')
        await engine.perform_completion(
            context, history, incoming_messages,
            server_config, client_config, completion_opts, signals
        )

    print("Testing 'full' format")  # Debug print
    full_signal_capture = SignalCaptureHandler()
    # Test with 'full' format
    with Signals().connected_to([
        full_signal_capture,
        StdoutCompletionStreamer('full', full_output)
    ]) as signals:
        client_config = ClientConfig(interactive=False, format='full')
        await engine.perform_completion(
            context, history, incoming_messages,
            server_config, client_config, completion_opts, signals
        )

    text_filtered_signals = text_signal_capture.filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])
    full_filtered_signals = full_signal_capture.filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])

    print(f"Text filtered signals: {text_filtered_signals}")  # Debug print
    print(f"Full filtered signals: {full_filtered_signals}")  # Debug print
    print(f"Text result: {repr(text_output.getvalue())}")  # Debug print
    print(f"Full result: {repr(full_output.getvalue())}")  # Debug print

    text_result = text_output.getvalue()
    full_result = full_output.getvalue()

    # Assertions for signals
    assert text_filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Text format signals should match the expected sequence"

    assert full_filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Full format signals should match the expected sequence"

    assert text_result == "\n> Previous history\n> \n> Short answer. 1+1=\n> \n> ", "Text format should contain the formatted response"
    assert full_result == "Previous history\n\nShort answer. 1+1=\n\n**assistant>** \n> Previous history\n> \n> Short answer. 1+1=\n> \n> \n\n", "Full format should contain history, input, and formatted response"
