import contextlib
import io
from typing import Iterator

import pytest

from taskmates.config.client_config import ClientConfig
from taskmates.contexts import Contexts
from taskmates.core.chat_session import ChatSession
from taskmates.core.signal_receivers.signals_collector import SignalsCollector
from taskmates.io.history_sink import HistorySink
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.sdk.taskmates_extension import TaskmatesExtension
from taskmates.signals.signals import Signals


class TestExtension(TaskmatesExtension):
    @property
    def name(self) -> str:
        return "TestExtension"

    @contextlib.contextmanager
    def completion_context(self, history: str | None,
                           incoming_messages: list[str],
                           contexts: Contexts) -> Iterator[tuple[str | None, list[str], Contexts]]:
        yield "modified_history", ["modified_messages"], {"modified_contexts": True}


class CaptureContext(TaskmatesExtension):
    def __init__(self):
        self.captured_args = {}

    @property
    def name(self) -> str:
        return "CaptureContext"

    @contextlib.contextmanager
    def completion_context(self, *args):
        self.captured_args['completion_context'] = args
        yield args

    @contextlib.contextmanager
    def completion_step_context(self, *args):
        self.captured_args['completion_step_context'] = args
        yield args


@pytest.mark.asyncio
async def test_chat_session_history(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    signal_capture = SignalsCollector()
    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    history_sink = HistorySink(history_file)

    with Signals().connected_to([signal_capture, history_sink]) as signals:
        engine = ChatSession(history=history, incoming_messages=incoming_messages, contexts=contexts, signals=signals)
        await engine.resume()

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
async def test_chat_session_stdout_streamer(tmp_path, contexts):
    text_output = io.StringIO()
    full_output = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    print("Testing 'text' format")  # Debug print
    text_signal_capture = SignalsCollector()
    # Test with 'text' format
    with Signals().connected_to([
        text_signal_capture,
        StdoutCompletionStreamer('text', text_output)
    ]) as signals:
        contexts['client_config'] = ClientConfig(interactive=False, format='text')
        engine = ChatSession(history=history, incoming_messages=incoming_messages, contexts=contexts, signals=signals)
        await engine.resume()

    print("Testing 'full' format")  # Debug print
    full_signal_capture = SignalsCollector()
    # Test with 'full' format
    with Signals().connected_to([
        full_signal_capture,
        StdoutCompletionStreamer('full', full_output)
    ]) as signals:
        contexts['client_config'] = ClientConfig(interactive=False, format='full')
        engine = ChatSession(history=history, incoming_messages=incoming_messages, contexts=contexts, signals=signals)
        await engine.resume()

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
