import asyncio
import io
import textwrap

import pytest

from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.core.run import RUN
from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.core.io.listeners.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
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
    jobs = [signal_capturer]
    await CliComplete(contexts=contexts, jobs=jobs).run(history_path=str(history_file),
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
    jobs = [
        signal_capturer,
        WriteMarkdownChatToStdout('text', text_output)
    ]
    contexts['client_config'].update(dict(interactive=False, format='text'))
    await CliComplete(contexts=contexts, jobs=jobs).run(history_path=str(history_file),
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
    jobs = [
        signal_capturer,
        WriteMarkdownChatToStdout('full', full_output)
    ]
    contexts['client_config'].update(dict(interactive=False, format='full'))
    await CliComplete(contexts=contexts, jobs=jobs).run(history_path=str(history_file),
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


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_interrupt_tool(tmp_path, contexts):
    markdown_chat = textwrap.dedent("""
    How much is 1 + 1?

    **assistant>**

    How much is 1 + 1?

    ###### Steps

    - Run Shell Command [1] `{"cmd":"echo 2; sleep 5; echo fail"}`

    """)

    captured_output = io.StringIO()
    signal_capturer = SignalsCapturer()
    jobs = [signal_capturer, WriteMarkdownChatToStdout('text', captured_output)]

    cli_complete = CliComplete(contexts=contexts, jobs=jobs)
    task = asyncio.create_task(cli_complete.run(incoming_messages=[markdown_chat]))

    # Wait for the "2" to be printed
    while "2" not in str(signal_capturer.captured_signals):
        await asyncio.sleep(0.1)

    # Send interrupt
    run = RUN.get()
    await run.control.interrupt_request.send_async({})

    try:
        await task
    except asyncio.CancelledError:
        pass

    output = captured_output.getvalue()

    expected_response = textwrap.dedent("""\
    ###### Execution: Run Shell Command [1]

    <pre class='output' style='display:none'>
    2
    --- INTERRUPT ---
    
    Exit Code: -2
    </pre>
    -[x] Done

    """)

    assert output == expected_response
