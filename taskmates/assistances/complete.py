import asyncio
from typing import Unpack

from typeguard import typechecked

from taskmates.assistances.async_complete import async_complete
from taskmates.config import CompletionOpts


@typechecked
def complete(markdown,
             **completion_opts: Unpack[CompletionOpts]):
    return asyncio.run(async_complete(markdown, **completion_opts))
