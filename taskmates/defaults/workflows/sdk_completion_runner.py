from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.core.run import Run
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.types import RunOpts


class SdkCompletionRunner:
    def __init__(self, *,
                 run_opts: RunOpts = None
                 ):
        self.contexts = SdkContextBuilder(run_opts or {}).build()

    @typechecked
    async def run(self, markdown_chat: str):
        with Run(contexts=self.contexts):
            steps = {
                "markdown_complete": MarkdownComplete()
            }

            return await steps["markdown_complete"].run(**{"markdown_chat": markdown_chat})


async def test_sdk_workflow(tmp_path):
    markdown = "Hello."

    runner = SdkCompletionRunner(run_opts={"model": "quote", })
    result = await runner.run(markdown_chat=markdown)

    assert result == '\n> Hello.\n\n'
