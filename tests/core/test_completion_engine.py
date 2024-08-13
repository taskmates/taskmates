import contextlib
import io
from typing import Iterator
from uuid import uuid4

import pytest

from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.contexts import Contexts
from taskmates.core.completion_engine import CompletionEngine
from taskmates.core.signal_receivers.signals_collector import SignalsCollector
from taskmates.io.history_sink import HistorySink
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.sdk.extension_manager import EXTENSION_MANAGER, ExtensionManager
from taskmates.sdk.taskmates_extension import TaskmatesExtension
from taskmates.signals.signals import Signals


class TestExtension(TaskmatesExtension):
    @property
    def name(self) -> str:
        return "TestExtension"

    @contextlib.contextmanager
    def completion_context(self, history: str | None,
                           incoming_messages: list[str],
                           contexts: Contexts,
                           signals: Signals,
                           states: dict) -> Iterator[tuple[str | None, list[str], Contexts, Signals, dict]]:
        modified_history = "Modified: " + (history or "")
        modified_messages = ["Modified: " + msg for msg in incoming_messages]
        modified_contexts = contexts.copy()
        modified_contexts['test_extension'] = {'modified': True}

        yield modified_history, modified_messages, modified_contexts, signals, states


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


@pytest.fixture
def contexts(tmp_path):
    return {
        "completion_context": {
            "request_id": str(uuid4()),
            "cwd": str(tmp_path),
            "env": {},
            "markdown_path": str(tmp_path / "chat.md")
        },
        "step_context": {
            "current_step": 1,
        },
        "server_config": ServerConfig(),
        "client_config": ClientConfig(interactive=False, endpoint="local"),
        "completion_opts": CompletionOpts(model="quote", template_params={}, taskmates_dirs=[]),
    }


@pytest.mark.asyncio
async def test_completion_engine_history(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    signal_capture = SignalsCollector()
    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    history_sink = HistorySink(history_file)

    engine = CompletionEngine()
    signals = Signals()

    with signals.connected_to([signal_capture, history_sink]):
        await engine.perform_completion(
            history,
            incoming_messages,
            contexts,
            signals,
            states={}
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
async def test_completion_engine_stdout_streamer(tmp_path, contexts):
    engine = CompletionEngine()

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
        await engine.perform_completion(
            history,
            incoming_messages,
            contexts,
            signals,
            states={}
        )

    print("Testing 'full' format")  # Debug print
    full_signal_capture = SignalsCollector()
    # Test with 'full' format
    with Signals().connected_to([
        full_signal_capture,
        StdoutCompletionStreamer('full', full_output)
    ]) as signals:
        contexts['client_config'] = ClientConfig(interactive=False, format='full')
        await engine.perform_completion(
            history, incoming_messages,
            contexts, signals,
            states={}
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


@pytest.mark.asyncio
async def test_completion_engine_with_extension_manager(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    # Create a real ExtensionManager with our CaptureContext extension
    capture_extension = CaptureContext()
    extension_manager = ExtensionManager([capture_extension])

    # Replace the global EXTENSION_MANAGER with our test instance
    original_extension_manager = EXTENSION_MANAGER.get()
    EXTENSION_MANAGER.set(extension_manager)

    try:
        engine = CompletionEngine()
        signals = Signals()
        signal_capture = SignalsCollector()

        with signals.connected_to([signal_capture]):
            await engine.perform_completion(
                history,
                incoming_messages,
                contexts,
                signals,
                states={}
            )

        # Check if the variables were correctly captured by the extension
        assert 'completion_context' in capture_extension.captured_args, "The completion_context should have been captured"
        assert 'completion_step_context' in capture_extension.captured_args, "The completion_step_context should have been captured"

        completion_context_args = capture_extension.captured_args['completion_context']
        assert completion_context_args[0] == history, "The history should have been captured correctly"
        assert completion_context_args[1] == incoming_messages, "The incoming messages should have been captured correctly"
        assert completion_context_args[2] == contexts, "The contexts should have been captured correctly"
        assert isinstance(completion_context_args[3], Signals), "The signals object should have been captured"
        assert isinstance(completion_context_args[4], dict), "The states should have been captured as a dictionary"

        # Check if the signals were still processed correctly
        filtered_signals = signal_capture.filter_signals(['history', 'incoming_message'])
        assert filtered_signals == [
            ('history', 'Initial history\n'),
            ('incoming_message', 'Incoming message')
        ], "The signals should have been processed correctly"

    finally:
        # Restore the original EXTENSION_MANAGER
        EXTENSION_MANAGER.set(original_extension_manager)


@pytest.mark.asyncio
async def test_completion_step_context(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    # Create a real ExtensionManager with our CaptureContext extension
    capture_extension = CaptureContext()
    extension_manager = ExtensionManager([capture_extension])

    # Replace the global EXTENSION_MANAGER with our test instance
    original_extension_manager = EXTENSION_MANAGER.get()
    EXTENSION_MANAGER.set(extension_manager)

    try:
        engine = CompletionEngine()
        signals = Signals()

        await engine.perform_completion(
            history,
            incoming_messages,
            contexts,
            signals,
            states={}
        )

        # Check if the completion_step_context was captured
        assert 'completion_step_context' in capture_extension.captured_args, "The completion_step_context should have been captured"

        completion_step_context_args = capture_extension.captured_args['completion_step_context']
        assert isinstance(completion_step_context_args[0], dict), "The chat should have been captured as a dictionary"
        assert isinstance(completion_step_context_args[1], dict), "The step_contexts should have been captured as a dictionary"
        assert isinstance(completion_step_context_args[2], Signals), "The signals object should have been captured"
        assert completion_step_context_args[3].__class__.__name__ == 'ReturnValueCollector', "The return_value_processor should have been captured"
        assert completion_step_context_args[4].__class__.__name__ == 'InterruptedOrKilledCollector', "The interruption_handler should have been captured"
        assert completion_step_context_args[5].__class__.__name__ == 'MaxStepsManager', "The max_steps_manager should have been captured"
        assert isinstance(completion_step_context_args[6], dict), "The states should have been captured as a dictionary"

    finally:
        # Restore the original EXTENSION_MANAGER
        EXTENSION_MANAGER.set(original_extension_manager)
