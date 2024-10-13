import pytest

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.defaults.workflows.sdk_completion_runner import SdkCompletionRunner


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime):
    contexts = SdkContextBuilder({
        "model": "quote",
    }).build()
    return contexts


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path, contexts):
    markdown = "Test markdown for SDK workflow"

    workflow = SdkCompletionRunner(run_opts=contexts["run_opts"])
    result = await workflow.run(markdown_chat=markdown)

    assert result == '\n> Test markdown for SDK workflow\n\n'

# TODO
# @pytest.mark.asyncio
# @pytest.mark.parametrize("format_type", ['text', 'full'])
# async def test_sdk_workflow_format(tmp_path, contexts, format_type):
#     markdown = f"Test markdown for SDK workflow with {format_type} format"
#
#     contexts['runner_config'].update(dict(interactive=False, format=format_type))
#
#     captured_signals = CapturedSignals()
#     jobs = [
#         captured_signals
#     ]
#     workflow = SdkCompletionRunner(contexts=contexts, jobs=jobs)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == f"\n> Test markdown for SDK workflow with {format_type} format\n\n"


# TODO
# @typechecked
# @pytest.mark.asyncio
# async def test_sdk_workflow_interrupt(tmp_path, contexts):
#     markdown = "Test markdown for SDK workflow interrupt"
#
#     captured_signals = CapturedSignals()
#     jobs = [captured_signals]
#     workflow = SdkCompletionRunner(contexts=contexts, jobs=jobs)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == '\n> Test markdown for SDK workflow interrupt\n\n'
