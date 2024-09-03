# import pytest
#
# from taskmates.context_builders.test_context_builder import TestContextBuilder
# from taskmates.core.runner import Runner
# from taskmates.core.signal_receivers.signals_collector import SignalsCollector
# from taskmates.core.signals import Signals
# from taskmates.lib.context_.temp_context import temp_context
# from taskmates.runner.contexts.contexts import CONTEXTS
#
#
# @pytest.fixture(autouse=True)
# def contexts(taskmates_runtime, tmp_path):
#     contexts = TestContextBuilder(tmp_path).build()
#     with temp_context(CONTEXTS, contexts):
#         contexts["completion_opts"]["workflow"] = "github_issue"
#         yield contexts
#
#
# @pytest.mark.asyncio
# async def test_github_issue_workflow(tmp_path, contexts):
#     inputs = {"repo_name": "taskmates/demo", "issue_number": 1}
#
#     signal_capture = SignalsCollector()
#
#     with Signals().connected_to([signal_capture]):
#
#         await Runner().run(inputs=inputs, contexts=contexts)
#
#
#     interesting_signals = ['incoming_message', 'input_formatting', 'error']
#     filtered_signals = signal_capture.filter_signals(interesting_signals)
#
#     assert filtered_signals == [('history', 'Initial history\n'),
#                                 ('input_formatting', '\n'),
#                                 ('incoming_message', 'Incoming message'),
#                                 ('input_formatting', '\n\n')]
