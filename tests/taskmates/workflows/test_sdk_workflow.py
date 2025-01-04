import pytest

from taskmates.workflows.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.workflows.runners.sdk_completion_runner import SdkCompletionRunner


@pytest.fixture(autouse=True)
def context(taskmates_runtime):
    contexts = SdkContextBuilder({
        "model": "quote",
    }).build()
    return contexts


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path, context):
    markdown = "Test markdown for SDK workflow"

    workflow = SdkCompletionRunner(run_opts=context["run_opts"])
    result = await workflow.run(markdown_chat=markdown)

    assert result == '\n> Test markdown for SDK workflow\n\n'

# TODO
# @pytest.mark.asyncio
# @pytest.mark.parametrize("format_type", ['text', 'full'])
# async def test_sdk_workflow_format(tmp_path, context, format_type):
#     markdown = f"Test markdown for SDK workflow with {format_type} format"
#
#     context['runner_config'].update(dict(interactive=False, format=format_type))
#
#     captured_signals = CapturedSignals()
#     daemons = [
#         captured_signals
#     ]
#     workflow = SdkCompletionRunner(context=context, daemons=daemons)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == f"\n> Test markdown for SDK workflow with {format_type} format\n\n"


# TODO
# @typechecked
# @pytest.mark.asyncio
# async def test_sdk_workflow_interrupt(tmp_path, context):
#     markdown = "Test markdown for SDK workflow interrupt"
#
#     captured_signals = CapturedSignals()
#     daemons = [captured_signals]
#     workflow = SdkCompletionRunner(context=context, daemons=daemons)
#     result = await workflow.run(markdown_chat=markdown)
#
#     assert result == '\n> Test markdown for SDK workflow interrupt\n\n'
