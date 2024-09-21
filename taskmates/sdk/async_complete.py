from typing import Unpack

from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.sdk.handlers.return_value_handler import ReturnValueHandler
from taskmates.types import CompletionOpts


@typechecked
async def async_complete(markdown,
                         **completion_opts: Unpack[CompletionOpts]):
    return_value_handler = ReturnValueHandler()

    contexts = SdkContextBuilder(completion_opts).build()
    jobs = [return_value_handler]
    await MarkdownComplete(contexts=contexts, jobs=jobs).run(current_markdown=markdown)

    return return_value_handler.get_return_value()
