# import asyncio
# import io
# import textwrap
#
# import pytest
#
# from taskmates.core.workflow_engine.environment import environment
# from taskmates.core.workflow_engine.run import RUN
# from taskmates.runtimes.tests.test_context_builder import TestContextBuilder
# from taskmates.runtimes.cli.signals.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
#
#
# @pytest.fixture(autouse=True)
# def contexts(taskmates_runtime, tmp_path):
#     contexts = TestContextBuilder(tmp_path).build()
#     contexts["run_opts"]["workflow"] = "cli_complete"
#     return contexts
#
#
# @pytest.mark.asyncio
# async def test_format_text(tmp_path, contexts):
#     string_io = io.StringIO()
#
#     history = "Previous history\n"
#     incoming_messages = ["Short answer. 1+1="]
#
#     history_file = tmp_path / "history.txt"
#     history_file.write_text(history)
#
#     @environment(fulfillers={'daemons': lambda: [WriteMarkdownChatToStdout('text', string_io)]})
#     async def attempt_format_text(contexts, history_file, incoming_messages):
#         contexts['runner_config'].update(dict(interactive=False, format='text'))
#         workflow = CliComplete()
#         await workflow.fulfill(history_path=str(history_file),
#                                incoming_messages=incoming_messages)
#
#         filtered_signals = RUN.get().state["captured_signals"].filter_signals(
#             ['history', 'incoming_message', 'input_formatting', 'error'])
#         return filtered_signals
#
#     filtered_signals = await attempt_format_text(contexts, history_file, incoming_messages)
#
#     text_result = string_io.getvalue()
#
#     # Assertions for signals
#     assert filtered_signals == [
#         ('history', 'Previous history\n'),
#         ('input_formatting', '\n'),
#         ('incoming_message', 'Short answer. 1+1='),
#         ('input_formatting', '\n\n')
#     ], "Text format signals should match the expected sequence"
#
#     assert text_result == "\n> Previous history\n> \n> Short answer. 1+1=\n> \n> \n\n", "Text format should contain the formatted response"
#
#
# @pytest.mark.asyncio
# async def test_format_full(tmp_path, contexts):
#     string_io = io.StringIO()
#
#     history = "Previous history\n"
#     incoming_messages = ["Short answer. 1+1="]
#
#     history_file = tmp_path / "history.txt"
#     history_file.write_text(history)
#
#     contexts['runner_config'].update(dict(interactive=False, format='full'))
#
#     @environment(fulfillers={'daemons': lambda: [WriteMarkdownChatToStdout('full', string_io)]})
#     async def attempt_format_full(string_io, history_file, incoming_messages):
#         workflow = CliComplete()
#         await workflow.fulfill(history_path=str(history_file),
#                                incoming_messages=incoming_messages)
#
#         filtered_signals = RUN.get().state["captured_signals"].filter_signals(
#             ['history', 'incoming_message', 'input_formatting', 'error'])
#
#         full_result = string_io.getvalue()
#         return filtered_signals, full_result
#
#     filtered_signals, full_result = await attempt_format_full(string_io, history_file, incoming_messages)
#
#     assert filtered_signals == [
#         ('history', 'Previous history\n'),
#         ('input_formatting', '\n'),
#         ('incoming_message', 'Short answer. 1+1='),
#         ('input_formatting', '\n\n')
#     ], "Full format signals should match the expected sequence"
#
#     assert full_result == "Previous history\n\nShort answer. 1+1=\n\n**assistant>** \n> Previous history\n> \n> Short answer. 1+1=\n> \n> \n\n", "Full format should contain history, input, and formatted response"
#
#
# @pytest.mark.asyncio
# @pytest.mark.timeout(10)
# async def test_interrupt_tool(tmp_path, contexts):
#     markdown_chat = textwrap.dedent("""
#     How much is 1 + 1?
#
#     **assistant>**
#
#     How much is 1 + 1?
#
#     ###### Steps
#
#     - Run Shell Command [1] `{"cmd":"echo 2; sleep 5; echo fail"}`
#
#     """)
#
#     string_io = io.StringIO()
#
#     @environment(fulfillers={'daemons': lambda: [WriteMarkdownChatToStdout('text', string_io)]})
#     async def attempt_interrupt_tool(string_io, markdown_chat):
#         workflow = CliComplete()
#         task = asyncio.create_task(workflow.fulfill(incoming_messages=[markdown_chat]))
#
#         run = RUN.get()
#
#         # Wait for the "2" to be printed
#         while "2" not in string_io.getvalue():
#             await asyncio.sleep(0.1)
#
#         # Send interrupt
#         await run.execution_context.emits["control"].interrupt_request.send_async({})
#
#         try:
#             await task
#         except asyncio.CancelledError:
#             pass
#
#         output = string_io.getvalue()
#         return output
#
#     output = await attempt_interrupt_tool(string_io, markdown_chat)
#
#     expected_response = textwrap.dedent("""\
#     ###### Execution: Run Shell Command [1]
#
#     <pre class='output' style='display:none'>
#     2
#     --- INTERRUPT ---
#
#     Exit Code: -2
#     </pre>
#     -[x] Done
#
#     """)
#
#     assert output == expected_response
