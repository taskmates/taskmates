import pytest
from typeguard import typechecked

from taskmates.core.io.listeners.signals_capturer import SignalsCapturer
from taskmates.core.job import Job
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.runner.contexts.contexts import Contexts
from taskmates.sdk.handlers.return_value_handler import ReturnValueHandler


class SdkComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, Job] | list[Job] = None,
                 ):
        super().__init__(contexts=contexts, jobs=jobs)
        self.jobs["call_result"] = ReturnValueHandler()

    @typechecked
    async def run(self, current_markdown: str):
        await MarkdownComplete().run(
            current_markdown=current_markdown
        )

        return self.jobs["call_result"].get_return_value()


@pytest.mark.asyncio
async def test_sdk_workflow(tmp_path, contexts):
    markdown = "Test markdown for SDK workflow"

    signal_capturer = SignalsCapturer()
    jobs = [signal_capturer]
    workflow = SdkComplete(contexts=contexts, jobs=jobs)
    result = await workflow.run(current_markdown=markdown)

    # TODO
    # filtered_signals = signal_capturer.captured_signals
    # assert filtered_signals == ()
    #
    assert result == '\n> Test markdown for SDK workflow\n\n'
