import io

import pytest

from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.core.io.listeners.stdout_completion_streamer import StdoutCompletionStreamer
from taskmates.defaults.workflows.cli_complete import CliComplete


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    contexts["completion_opts"]["workflow"] = "cli_complete"
    return contexts


@pytest.mark.asyncio
async def test_cli_workflow(tmp_path, contexts):
    history = "Initial history\n"
    incoming_messages = ["Incoming message"]

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    signal_capturer = SignalsCapturer()
    processors = [signal_capturer]
    await CliComplete(contexts=contexts, processors=processors).run(history_path=str(history_file),
                                                                    incoming_messages=incoming_messages)

    interesting_signals = ['history', 'incoming_message', 'input_formatting', 'error']
    filtered_signals = signal_capturer.filter_signals(interesting_signals)

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

    signal_capturer = SignalsCapturer()
    processors = [
        signal_capturer,
        StdoutCompletionStreamer('text', text_output)
    ]
    contexts['client_config'].update(dict(interactive=False, format='text'))
    await CliComplete(contexts=contexts, processors=processors).run(history_path=str(history_file),
                                                                    incoming_messages=incoming_messages)

    text_filtered_signals = signal_capturer.filter_signals(
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

    signal_capturer = SignalsCapturer()
    processors = [
        signal_capturer,
        StdoutCompletionStreamer('full', full_output)
    ]
    contexts['client_config'].update(dict(interactive=False, format='full'))
    await CliComplete(contexts=contexts, processors=processors).run(history_path=str(history_file),
                                                                    incoming_messages=incoming_messages)

    full_filtered_signals = signal_capturer.filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])

    full_result = full_output.getvalue()

    assert full_filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Full format signals should match the expected sequence"

    assert full_result == "Previous history\n\nShort answer. 1+1=\n\n**assistant>** \n> Previous history\n> \n> Short answer. 1+1=\n> \n> \n\n", "Full format should contain history, input, and formatted response"
