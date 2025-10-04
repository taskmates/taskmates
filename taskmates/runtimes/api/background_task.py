import asyncio
from contextlib import contextmanager


@contextmanager
def background_task(fn):
    task = asyncio.create_task(fn())
    try:
        yield
    finally:
        if task and not task.done():
            task.cancel()
