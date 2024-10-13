import asyncio
from functools import wraps
from typing import Callable, Optional, Any

import pytest

from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.run import RUN
from taskmates.workflows.contexts.context import Context, default_taskmates_dirs


async def ensure_async(fn: Callable) -> Any:
    if asyncio.iscoroutinefunction(fn):
        return await fn()
    return fn()


def fulfills(
        outcome: str,
        context_fn: Callable = lambda: RUN.get().context,
        state_fn: Callable = lambda: RUN.get().state,
        signals_fn: Callable = lambda: {},
        daemons_fn: Optional[Callable] = lambda: {}
):
    def decorator(steps_fn: Callable):
        @wraps(steps_fn)
        async def _fulfills_wrapper(*args, **kwargs):
            run = RUN.get()

            context = await ensure_async(context_fn)
            state = await ensure_async(state_fn)
            signals = await ensure_async(signals_fn)
            daemons = await ensure_async(daemons_fn) if daemons_fn else None

            # Check cache in parent run
            args_key = {"args": args, "kwargs": kwargs} if args or kwargs else None
            existing_result = run.get_result(outcome, args_key)
            if existing_result is not None:
                return existing_result

            with run.request(outcome=outcome).attempt(
                    context=context,
                    daemons=daemons,
                    signals=signals
            ) as run:
                if state:
                    run.state.update(state)

                # Execute and cache in parent run
                result = await steps_fn(*args, **kwargs)
                run.set_result(outcome, args_key, result)
                return result

        return _fulfills_wrapper

    return decorator


@pytest.fixture
def test_context() -> Context:
    return Context(
        runner_config={
            "interactive": False,
            "format": "full",
            "taskmates_dirs": default_taskmates_dirs
        },
        runner_environment={
            "markdown_path": "test.md",
            "cwd": "/tmp"
        },
        run_opts={
            "model": "test",
            "max_steps": 10
        }
    )


@pytest.fixture
def run(test_context):
    request = Objective(outcome="test")
    run = request.attempt(context=test_context)
    token = RUN.set(run)
    yield run
    RUN.reset(token)


async def test_fulfills_decorator_basic_functionality(run):
    # Test that the decorator properly wraps an async function
    @fulfills(outcome="test_purpose")
    async def test_function(arg1, arg2):
        return arg1 + arg2

    result = await test_function(1, 2)
    assert result == 3


async def test_fulfills_decorator_caching(run):
    call_count = 0

    @fulfills(outcome="cached_purpose")
    async def cached_function(arg1, arg2):
        nonlocal call_count
        call_count += 1
        return arg1 + arg2

    # First call should execute the function
    result1 = await cached_function(1, 2)
    assert result1 == 3
    assert call_count == 1

    # Second call with same args should return cached result
    result2 = await cached_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # Call count should not increase

    # Call with different args should execute the function
    result3 = await cached_function(2, 3)
    assert result3 == 5
    assert call_count == 2


async def test_fulfills_decorator_manual_cache_set(run):
    @fulfills(outcome="manual_cache")
    async def cached_function(arg1, arg2):
        return arg1 + arg2

    # Set a cached value for specific args
    run.set_result("manual_cache", {"args": (1, 2), "kwargs": {}}, 42)

    # Function call should return the cached value
    result = await cached_function(1, 2)
    assert result == 42


async def test_fulfills_decorator_purpose_only_cache(run):
    @fulfills(outcome="purpose_cache")
    async def cached_function(arg1, arg2):
        return arg1 + arg2

    # Set a cached value for the outcome only
    run.set_result("purpose_cache", None, 42)

    # Any call to the function should return the cached value
    result1 = await cached_function(1, 2)
    assert result1 == 42

    result2 = await cached_function(3, 4)
    assert result2 == 42
