from typing import Unpack

import pytest
from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.defaults.workflows.sdk_complete import SdkComplete
from taskmates.types import CompletionOpts


@typechecked
async def async_complete(markdown: str, **completion_opts: Unpack[CompletionOpts]):
    contexts = SdkContextBuilder(completion_opts).build()
    workflow = SdkComplete(contexts=contexts)
    return await workflow.run(current_markdown=markdown)


@pytest.mark.asyncio
async def test_async_complete():
    markdown = "Test markdown for async_complete"
    result = await async_complete(markdown, model="quote")

    assert result == '\n> Test markdown for async_complete\n\n'
