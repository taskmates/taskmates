import pytest
from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.core.daemons.interrupt_request_mediator import InterruptRequestMediator
from taskmates.core.daemons.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.daemons.return_value import ReturnValue
from taskmates.core.run import Run
from taskmates.core.merge_jobs import merge_jobs
from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.runner.contexts.contexts import Contexts


class SdkComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, Run] | list[Run] = None,
                 ):
        control_flow_jobs = {
            "interrupt_request_mediator": InterruptRequestMediator(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
        }

        super().__init__(contexts=contexts, jobs=merge_jobs(jobs, control_flow_jobs))

    @typechecked
    async def run(self, markdown_chat: str):
        steps = {
            "markdown_complete": MarkdownComplete()
        }

        return await steps["markdown_complete"].run(**{"markdown_chat": markdown_chat})


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime):
    contexts = SdkContextBuilder({
        "model": "quote",
    }).build()
    return contexts


async def test_sdk_workflow(tmp_path, contexts):
    markdown = "Hello."

    signal_capturer = SignalsCapturer()
    jobs = [signal_capturer]
    workflow = SdkComplete(contexts=contexts, jobs=jobs)
    result = await workflow.run(markdown_chat=markdown)

    # TODO
    # filtered_signals = signal_capturer.captured_signals
    # assert filtered_signals == ()
    #
    assert result == '\n> Hello.\n\n'
