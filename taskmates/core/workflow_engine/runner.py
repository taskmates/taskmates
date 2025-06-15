import asyncio
from typing import Callable

import pytest


class Runner:
    def __init__(self, func: Callable, inputs: dict):
        self.func = func
        self.inputs = inputs
        self.run_task = None

    def start(self):
        self.run_task = asyncio.create_task(self._run())

    async def _run(self):
        return await self.func(**self.inputs)

    async def get_result(self):
        if self.run_task is None:
            raise RuntimeError("Runner has not been started")
        return await self.run_task


async def sample_callable(**kwargs):
    return sum(kwargs.values())


@pytest.mark.asyncio
async def test_runner_execution():
    runner = Runner(sample_callable, dict(a=1, b=2, c=3))
    runner.start()
    result = await runner.get_result()
    assert result == 6


@pytest.mark.asyncio
async def test_runner_not_started():
    runner = Runner(sample_callable, dict(a=1, b=2, c=3))
    with pytest.raises(RuntimeError, match="Runner has not been started"):
        await runner.get_result()
