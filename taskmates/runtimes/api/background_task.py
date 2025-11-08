import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def background_task(fn):
    task = asyncio.create_task(fn())
    try:
        yield
    finally:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


import pytest


async def test_background_task_runs_coroutine():
    """Test that background_task properly runs an async coroutine"""
    executed = []
    
    async def background_fn():
        executed.append("started")
        await asyncio.sleep(0.1)
        executed.append("finished")
    
    async with background_task(background_fn):
        await asyncio.sleep(0.05)
        assert executed == ["started"]
    
    # Task should be cancelled after context exit
    await asyncio.sleep(0.1)
    assert executed == ["started"]


async def test_background_task_cancels_on_exit():
    """Test that background_task cancels the task when exiting context"""
    cancelled = []
    
    async def background_fn():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.append("cancelled")
            raise
    
    async with background_task(background_fn):
        await asyncio.sleep(0.01)
    
    await asyncio.sleep(0.01)
    assert cancelled == ["cancelled"]


async def test_background_task_handles_completed_task():
    """Test that background_task handles tasks that complete before context exit"""
    completed = []
    
    async def background_fn():
        completed.append("done")
    
    async with background_task(background_fn):
        await asyncio.sleep(0.01)
    
    assert completed == ["done"]


async def test_background_task_with_exception():
    """Test that background_task properly handles exceptions in the background task"""
    error_raised = []
    
    async def background_fn():
        await asyncio.sleep(0.01)
        error_raised.append("error")
        raise ValueError("test error")
    
    async with background_task(background_fn):
        await asyncio.sleep(0.05)
    
    # The exception should be suppressed during cancellation
    assert error_raised == ["error"]
