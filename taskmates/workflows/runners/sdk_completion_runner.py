from typeguard import typechecked

from taskmates.types import RunOpts
from taskmates.workflow_engine.objective import Objective
from taskmates.workflows.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.workflows.markdown_complete import MarkdownComplete


class SdkCompletionRunner:
    def __init__(self, *,
                 run_opts: RunOpts = None
                 ):
        self.context = SdkContextBuilder(run_opts=run_opts or {}).build()

    @typechecked
    async def run(self, markdown_chat: str):
        async def attempt_sdk_completion(context, markdown_chat):
            with Objective(outcome="sdk_completion_runner").environment(context=context) as run:
                await run.signals["status"].start.send_async({})
                steps = {
                    "markdown_complete": MarkdownComplete()
                }

                return await steps["markdown_complete"].fulfill(**{"markdown_chat": markdown_chat})

        return await attempt_sdk_completion(self.context, markdown_chat)


async def test_sdk_workflow(tmp_path):
    markdown = "Hello."

    runner = SdkCompletionRunner(run_opts={"model": "quote", })
    result = await runner.run(markdown_chat=markdown)

    assert result == '\n> Hello.\n\n'
