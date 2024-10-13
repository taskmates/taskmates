from typing import Unpack

import pytest
from typeguard import typechecked

from taskmates.context_builders.sdk_context_builder import SdkContextBuilder
from taskmates.defaults.workflows.sdk_completion_runner import SdkCompletionRunner
from taskmates.types import RunOpts


@typechecked
async def async_complete(markdown: str, **run_opts: Unpack[RunOpts]):
    workflow = SdkCompletionRunner(run_opts=run_opts)
    return await workflow.run(markdown_chat=markdown)


@pytest.mark.asyncio
async def test_async_complete():
    markdown = "Test markdown for async_complete"
    result = await async_complete(markdown, model="quote")

    assert result == '\n> Test markdown for async_complete\n\n'
