import asyncio

from typeguard import typechecked

from taskmates.assistances.async_complete import async_complete


@typechecked
def complete(*args, **kwargs):
    return asyncio.run(async_complete(*args, **kwargs))
