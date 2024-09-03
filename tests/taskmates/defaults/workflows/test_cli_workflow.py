import io

import pytest

from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.core.runner import Runner
from taskmates.core.signal_receivers.signals_collector import SignalsCollector
from taskmates.core.signals import Signals
from taskmates.io.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.lib.context_.temp_context import temp_context
from taskmates.runner.contexts.contexts import CONTEXTS


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    with temp_context(CONTEXTS, contexts):
        contexts["completion_opts"]["workflow"] = "cli_complete"
        yield contexts


@pytest.mark.asyncio
async def test_cli_workflow(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    signal_capture = SignalsCollector()

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    with Signals().connected_to([signal_capture]):
        await Runner().run(inputs=dict(history_path=str(history_file),
                                       incoming_messages=incoming_messages, ),
                           contexts=contexts)

    interesting_signals = ['history', 'incoming_message', 'input_formatting', 'error']
    filtered_signals = signal_capture.filter_signals(interesting_signals)

    with open(history_file, "r") as f:
        history_content = f.read()

    assert filtered_signals == [('history', 'Initial history\n'),
                                ('input_formatting', '\n'),
                                ('incoming_message', 'Incoming message'),
                                ('input_formatting', '\n\n')]
    assert history_content == ('Initial history\n'
                               '\n'
                               'Incoming message\n'
                               '\n'
                               '**assistant>** \n'
                               '> Initial history\n'
                               '> \n'
                               '> Incoming message\n'
                               '> \n'
                               '> \n'
                               '\n')


@pytest.mark.asyncio
async def test_format_text(tmp_path, contexts):
    text_output = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    text_signal_capture = SignalsCollector()
    # Test with 'text' format
    with Signals().connected_to([
        text_signal_capture,
        StdoutCompletionStreamer('text', text_output)
    ]):
        contexts['client_config'].update(dict(interactive=False, format='text'))
        await Runner().run(inputs=dict(history_path=str(history_file),
                                       incoming_messages=incoming_messages),
                           contexts=contexts)

    full_signal_capture = SignalsCollector()
    # Test with 'full' format
    text_filtered_signals = text_signal_capture.filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])

    text_result = text_output.getvalue()

    # Assertions for signals
    assert text_filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Text format signals should match the expected sequence"

    assert text_result == "\n> Previous history\n> \n> Short answer. 1+1=\n> \n> ", "Text format should contain the formatted response"


@pytest.mark.asyncio
async def test_format_full(tmp_path, contexts):
    full_output = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    full_signal_capture = SignalsCollector()
    # Test with 'full' format
    with Signals().connected_to([
        full_signal_capture,
        StdoutCompletionStreamer('full', full_output)
    ]):
        contexts['client_config'].update(dict(interactive=False, format='full'))
        await Runner().run(inputs=dict(history_path=str(history_file), incoming_messages=incoming_messages),
                           contexts=contexts)

    full_filtered_signals = full_signal_capture.filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])

    full_result = full_output.getvalue()

    assert full_filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Full format signals should match the expected sequence"

    assert full_result == "Previous history\n\nShort answer. 1+1=\n\n**assistant>** \n> Previous history\n> \n> Short answer. 1+1=\n> \n> \n\n", "Full format should contain history, input, and formatted response"
