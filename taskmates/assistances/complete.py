import asyncio
from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.completion_opts import CompletionOpts
from taskmates.assistances.async_complete import async_complete


@typechecked
def complete(markdown, **completion_opts: Unpack[CompletionOpts]):
    return asyncio.run(async_complete(markdown, **completion_opts))
