import pytest

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.defaults.workflows.sdk_complete import SdkComplete


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime):
    contexts = SdkContextBuilder({
        "model": "quote",
    }).build()
    return contexts


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path, contexts):
    markdown = "Test markdown for SDK workflow"

    signal_capturer = SignalsCapturer()
    jobs = [signal_capturer]
    workflow = SdkComplete(contexts=contexts, jobs=jobs)
    result = await workflow.run(markdown_chat=markdown)

    assert result == '\n> Test markdown for SDK workflow\n\n'

# TODO
# @pytest.mark.asyncio
# @pytest.mark.parametrize("format_type", ['text', 'full'])
# async def test_sdk_workflow_format(tmp_path, contexts, format_type):
#     markdown = f"Test markdown for SDK workflow with {format_type} format"
#
#     contexts['client_config'].update(dict(interactive=False, format=format_type))
#
#     signal_capturer = SignalsCapturer()
#     jobs = [
#         signal_capturer
#     ]
#     workflow = SdkComplete(contexts=contexts, jobs=jobs)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == f"\n> Test markdown for SDK workflow with {format_type} format\n\n"


# TODO
# @typechecked
# @pytest.mark.asyncio
# async def test_sdk_workflow_interrupt(tmp_path, contexts):
#     markdown = "Test markdown for SDK workflow interrupt"
#
#     signal_capturer = SignalsCapturer()
#     jobs = [signal_capturer]
#     workflow = SdkComplete(contexts=contexts, jobs=jobs)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == '\n> Test markdown for SDK workflow interrupt\n\n'
