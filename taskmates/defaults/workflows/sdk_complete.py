import pytest
from typeguard import typechecked

from taskmates.core.execution_context import ExecutionContext, merge_jobs
from taskmates.core.daemons.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.daemons.return_value import ReturnValue
from taskmates.core.daemons.interrupt_request_mediator import InterruptRequestMediator
from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.runner.contexts.contexts import Contexts
from taskmates.sdk.handlers.call_result import CallResult


class SdkComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, ExecutionContext] | list[ExecutionContext] = None,
                 ):
        root_jobs = {
            # TODO: job state
            "interrupt_request_mediator": InterruptRequestMediator(),
            "interrupted_or_killed": InterruptedOrKilled(),
            # TODO: job output
            "return_value": ReturnValue(),
        }

        root_jobs["call_result"] = CallResult()
        super().__init__(contexts=contexts, jobs=merge_jobs(jobs, root_jobs))

    @typechecked
    async def run(self, markdown_chat: str):
        await MarkdownComplete().run(
            markdown_chat=markdown_chat
        )

        return self.jobs_registry["call_result"].get_return_value()


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path, contexts):
    markdown = "Test markdown for SDK workflow"

    signal_capturer = SignalsCapturer()
    jobs = [signal_capturer]
    workflow = SdkComplete(contexts=contexts, jobs=jobs)
    result = await workflow.run(markdown_chat=markdown)

    # TODO
    # filtered_signals = signal_capturer.captured_signals
    # assert filtered_signals == ()
    #
    assert result == '\n> Test markdown for SDK workflow\n\n'
