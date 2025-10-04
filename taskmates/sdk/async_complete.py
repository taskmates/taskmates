from typing import Unpack

import pytest
from typeguard import typechecked

from taskmates.core.workflow_engine.transaction import Objective, ObjectiveKey
from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
from taskmates.defaults.settings import Settings
from taskmates.types import RunOpts


@typechecked
async def async_complete(markdown: str, **run_opts: Unpack[RunOpts]):
    context = Settings().get()
    context["run_opts"].update(run_opts)

    instance = MarkdownCompletion(
        objective=Objective(key=ObjectiveKey(
            outcome=MarkdownCompletion.__name__,
            inputs={"markdown_chat": markdown}
        )),
        context=context
    )
    return await instance.fulfill()


@pytest.mark.asyncio
async def test_async_complete():
    markdown = "Test markdown for async_complete"
    result = await async_complete(markdown, model="quote", max_steps=2)

    assert result == '**assistant>** \n> Test markdown for async_complete\n> \n> \n\n'
