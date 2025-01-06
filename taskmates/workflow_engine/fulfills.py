from functools import wraps
from typing import Callable

import pytest
from jupyter_core.utils import ensure_async

from taskmates.workflow_engine.run import RUN, Objective, ObjectiveKey, Run
from taskmates.workflows.contexts.run_context import RunContext, default_taskmates_dirs


def fulfills(outcome: str):
    def decorator(fn: Callable):
        @wraps(fn)
        async def _fulfills_wrapper(*args, **kwargs):
            current_run = RUN.get()
            current_objective = current_run.objective

            # Check result in parent run
            args_key = {"args": args, "kwargs": kwargs} if args or kwargs else None
            existing_result = current_objective.get_future_result(outcome, args_key)
            if existing_result is not None:
                return existing_result

            sub_objective = Objective(key=ObjectiveKey(
                outcome=outcome,
                inputs={},  # TODO: review
                requesting_run=current_run
            ))

            sub_run = Run(objective=sub_objective,
                          context=current_run.context,
                          daemons={},
                          signals=current_run.signals,
                          state=current_run.state)

            with sub_run:
                # Execute and store result in parent run
                result = await ensure_async(fn(*args, **kwargs))
                current_objective.set_future_result(outcome, args_key, result)
                return result

        return _fulfills_wrapper

    return decorator


@pytest.fixture
def test_context() -> RunContext:
    return RunContext(
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
    run = Objective(key=ObjectiveKey(outcome="test_runner")).environment(context=test_context)
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
    run.objective.set_future_result("manual_cache", {"args": (1, 2), "kwargs": {}}, 42)

    # Function call should return the cached value
    result = await cached_function(1, 2)
    assert result == 42


@pytest.mark.skip
async def test_fulfills_decorator_purpose_only_cache(run):
    @fulfills(outcome="purpose_cache")
    async def cached_function(arg1, arg2):
        return arg1 + arg2

    # Set a cached value for the outcome only
    run.objective.set_future_result("purpose_cache", None, 42)

    # Any call to the function should return the cached value
    result1 = await cached_function(1, 2)
    assert result1 == 42

    result2 = await cached_function(3, 4)
    assert result2 == 42
