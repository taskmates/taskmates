import asyncio
import io
import textwrap

import pytest

from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.core.io.listeners.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
from taskmates.core.run import RUN, Run
from taskmates.defaults.workflows.cli_complete import CliComplete


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    contexts["run_opts"]["workflow"] = "cli_complete"
    return contexts


@pytest.mark.asyncio
async def test_format_text(tmp_path, contexts):
    string_io = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    with Run(jobs=[WriteMarkdownChatToStdout('text', string_io)]):
        contexts['runner_config'].update(dict(interactive=False, format='text'))
        workflow = CliComplete()
        await workflow.run(history_path=str(history_file),
                           incoming_messages=incoming_messages)

    last_run = workflow.last_run
    filtered_signals = last_run.jobs_registry["captured_signals"].filter_signals(
        ['history', 'incoming_message', 'input_formatting', 'error'])

    text_result = string_io.getvalue()

    # Assertions for signals
    assert filtered_signals == [
        ('history', 'Previous history\n'),
        ('input_formatting', '\n'),
        ('incoming_message', 'Short answer. 1+1='),
        ('input_formatting', '\n\n')
    ], "Text format signals should match the expected sequence"

    assert text_result == "\n> Previous history\n> \n> Short answer. 1+1=\n> \n> ", "Text format should contain the formatted response"


@pytest.mark.asyncio
async def test_format_full(tmp_path, contexts):
    string_io = io.StringIO()

    history = "Previous history\n"
    incoming_messages = ["Short answer. 1+1="]

    history_file = tmp_path / "history.txt"
    history_file.write_text(history)

    contexts['runner_config'].update(dict(interactive=False, format='full'))

    with Run(jobs=[WriteMarkdownChatToStdout('full', string_io)]):
        workflow = CliComplete()
        await workflow.run(history_path=str(history_file),
                           incoming_messages=incoming_messages)

        last_run = workflow.last_run
        filtered_signals = last_run.jobs_registry["captured_signals"].filter_signals(
            ['history', 'incoming_message', 'input_formatting', 'error'])

        full_result = string_io.getvalue()

    assert filtered_signals == [
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

    string_io = io.StringIO()

    with Run(jobs=[WriteMarkdownChatToStdout('text', string_io)]):
        workflow = CliComplete()
        task = asyncio.create_task(workflow.run(incoming_messages=[markdown_chat]))

        run = RUN.get()

        # Wait for the "2" to be printed
        while "2" not in str(run.jobs_registry["captured_signals"].get()):
            await asyncio.sleep(0.1)

        # Send interrupt
        await run.control.interrupt_request.send_async({})

        try:
            await task
        except asyncio.CancelledError:
            pass

        output = string_io.getvalue()

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
