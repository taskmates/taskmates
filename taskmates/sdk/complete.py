import asyncio
from typing import Unpack

from typeguard import typechecked

from taskmates.types import RunOpts
from taskmates.sdk.async_complete import async_complete


@typechecked
def complete(markdown,
             **run_opts: Unpack[RunOpts]):
    return asyncio.run(async_complete(markdown, **run_opts))
