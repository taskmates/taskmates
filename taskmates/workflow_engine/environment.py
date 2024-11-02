import asyncio
from functools import wraps
from typing import Callable, Optional

import pytest
from jupyter_core.utils import ensure_async

from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.run import RUN, Run
from taskmates.workflows.contexts.context import Context, default_taskmates_dirs


def environment(
        context_fn: Callable = lambda: RUN.get().context,
        state_fn: Callable = lambda: RUN.get().state,
        signals_fn: Callable = lambda: RUN.get().signals,
        daemons_fn: Optional[Callable] = lambda: {},
        results_fn: Callable = lambda: RUN.get().results
):
    def decorator(fn: Callable):
        @wraps(fn)
        async def _environment_wrapper(*args, **kwargs):
            run = RUN.get()

            context = await ensure_async(context_fn())
            state = await ensure_async(state_fn())
            signals = await ensure_async(signals_fn())
            daemons = await ensure_async(daemons_fn())
            results = await ensure_async(results_fn())

            forked_run = Run(
                objective=run.objective,
                context=context,
                state=state,
                results=results,
                signals=signals,
                daemons=daemons
            )

            with forked_run:
                if asyncio.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                return fn(*args, **kwargs)

        return _environment_wrapper

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
    run = Objective(outcome="test_runner").environment(context=test_context)
    token = RUN.set(run)
    yield run
    RUN.reset(token)


async def test_environment_decorator_basic_functionality(run):
    # Test that the decorator properly wraps an async function
    @environment()
    async def test_function():
        return RUN.get()

    result = await test_function()
    assert result is not run  # Should be a different run instance
    assert result.objective == run.objective  # But should have the same objective


# async def test_environment_decorator_state_isolation(run):
#     run.state['original'] = 'value'
#
#     @environment()
#     async def test_function():
#         current_run = RUN.get()
#         current_run.state['modified'] = 'new_value'
#         return current_run.state
#
#     result = await test_function()
#
#     # The forked run should have the original state
#     assert result['original'] == 'value'
#
#     # The modification should not affect the original run
#     assert 'modified' not in run.state
#
#     # The modification should be present in the forked state
#     assert result['modified'] == 'new_value'


async def test_environment_decorator_with_sync_function(run):
    @environment()
    def sync_function():
        return RUN.get()

    result = await sync_function()
    assert result is not run
    assert result.objective == run.objective


async def test_environment_decorator_nested(run):
    @environment()
    async def outer_function():
        outer_run = RUN.get()

        @environment()
        async def inner_function():
            return RUN.get()

        inner_run = await inner_function()
        return outer_run, inner_run

    outer_run, inner_run = await outer_function()

    assert outer_run is not run
    assert inner_run is not run
    assert inner_run is not outer_run
    assert inner_run.objective == outer_run.objective == run.objective
