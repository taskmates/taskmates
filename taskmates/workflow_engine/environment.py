import asyncio
from functools import wraps
from typing import Callable, Dict

import pytest
from jupyter_core.utils import ensure_async

from taskmates.workflow_engine.run import RUN, Run, Objective
from taskmates.workflows.contexts.run_context import RunContext, default_taskmates_dirs


def environment(fulfillers: Dict[str, Callable] | None = None):
    def decorator(fn: Callable):
        @wraps(fn)
        async def _environment_wrapper(*args, **kwargs):
            nonlocal fulfillers
            if fulfillers is None:
                fulfillers = {}

            default_fulfillers = {
                'objective': lambda: RUN.get().objective,
                'context': lambda: RUN.get().context,
                'state': lambda: RUN.get().state,
                'signals': lambda: RUN.get().signals,
                'daemons': lambda: {},
            }

            # Merge provided fulfillers with defaults
            effective_fulfillers = {**default_fulfillers, **fulfillers}

            objective = await ensure_async(effective_fulfillers['objective']())
            context = await ensure_async(effective_fulfillers['context']())
            state = await ensure_async(effective_fulfillers['state']())
            signals = await ensure_async(effective_fulfillers['signals']())
            daemons = await ensure_async(effective_fulfillers['daemons']())

            forked_run = Run(
                objective=objective,
                context=context,
                state=state,
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


async def test_environment_decorator_with_custom_fulfillers(run):
    custom_context = RunContext(
        runner_config={"interactive": True},
        runner_environment={},
        run_opts={}
    )

    custom_fulfillers = {
        'context': lambda: custom_context,
        'state': lambda: {'custom': 'state'},
    }

    @environment(fulfillers=custom_fulfillers)
    async def test_function():
        current_run = RUN.get()
        return current_run.context, current_run.state

    context, state = await test_function()
    assert context == custom_context
    assert state == {'custom': 'state'}


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


async def test_environment_decorator_partial_fulfillers(run):
    # Test that providing only some fulfillers works correctly
    custom_fulfillers = {
        'state': lambda: {'custom': 'state'}
    }

    @environment(fulfillers=custom_fulfillers)
    async def test_function():
        current_run = RUN.get()
        return current_run.context, current_run.state

    context, state = await test_function()
    assert context == run.context  # Should use default context
    assert state == {'custom': 'state'}  # Should use custom state
