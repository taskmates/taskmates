from contextlib import asynccontextmanager


@asynccontextmanager
async def ensure_async_context_manager(cm):
    """
    Wraps a synchronous context manager to make it async-compatible.
    If the input is already an async context manager, returns it as-is.
    """
    # Check if it's already an async context manager
    if hasattr(cm, '__aenter__') and hasattr(cm, '__aexit__'):
        async with cm as value:
            yield value
    else:
        # It's a sync context manager, wrap it
        with cm as value:
            yield value
