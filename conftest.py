import os
from typing import Iterable

import pytest
import pytest_socket
import tiktoken

from taskmates.config.load_participant_config import load_cache
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.kernel_manager import get_kernel_manager
from taskmates.runtimes.tests.test_context_builder import TestContextBuilder
from taskmates.runtimes.tests.signals.captured_signals_daemon import CapturedSignalsDaemon
from taskmates.runtimes.cli.signals.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
from taskmates.core.workflows.states.captured_signals import CapturedSignals
from taskmates.load_env_files import load_env_for_environment
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.core.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.core.workflow_engine.run import Run, to_daemons_dict, Objective, ObjectiveKey


# def pytest_configure(config):
#     # Set up logging
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)
#
#     # Ensure the logger has at least one handler.
#     if not logger.hasHandlers():
#         handler = logging.StreamHandler()
#         handler.setLevel(logging.INFO)
#         logger.addHandler(handler)


def pytest_runtest_setup(item):
    # Force the tiktoken encoding to be downloaded before disabling the network
    tiktoken.encoding_for_model("gpt-4")

    # If the test is marked with 'integration', enable socket connections
    if "integration" in item.keywords:
        env = "integration_test"
        pytest_socket.enable_socket()
    else:
        env = "test"
        pytest_socket.socket_allow_hosts(['127.0.0.1', '::1', 'fe80::1'])

    os.environ["TASKMATES_ENV"] = env

    load_env_for_environment(env)


def pytest_collection_modifyitems(config, items):
    run_first = [item for item in items if 'slow' not in item.keywords]
    run_last = [item for item in items if 'slow' in item.keywords]
    items[:] = run_first + run_last


@pytest.fixture
def subject(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(autouse=True)
def reset_cache(taskmates_runtime):
    load_cache.clear()


@pytest.fixture(autouse=True)
def taskmates_runtime():
    try:
        TASKMATES_RUNTIME.get().initialize()
        yield TASKMATES_RUNTIME.get()
    finally:
        TASKMATES_RUNTIME.get().shutdown()


@pytest.fixture
def run_opts(request):
    if "integration" in request.node.keywords:
        return {
            "model": "claude-3-7-sonnet-20250219",
            "max_steps": 100
        }
    else:
        return {
            "model": "quote",
            "max_steps": 2
        }


@pytest.fixture
def context(request, taskmates_runtime, run_opts, tmp_path):
    return TestContextBuilder(tmp_path).build(run_opts)


@pytest.fixture
def daemons(request):
    if "integration" in request.node.keywords:
        return [WriteMarkdownChatToStdout("full")]
    else:
        return [CapturedSignalsDaemon()]


@pytest.fixture(autouse=True)
def run(request, taskmates_runtime, context, daemons) -> Iterable[Run]:
    with Run(objective=Objective(key=ObjectiveKey(outcome=request.node.name)),
             context=context,
             daemons=to_daemons_dict(daemons),
             signals=default_environment_signals(),
             state={"captured_signals": CapturedSignals()}) as run:
        yield run


@pytest.fixture(scope="function", autouse=True)
async def teardown_after_all_tests(taskmates_runtime):
    yield

    kernel_manager = get_kernel_manager()
    await kernel_manager.cleanup_all()
    kernel_manager._kernel_pool.clear()
    kernel_manager._client_pool.clear()
    kernel_manager._cell_trackers.clear()


# @pytest.fixture(autouse=True)
# def event_loop_fixture():
#     """Fixture to properly handle event loop cleanup."""
#     import asyncio
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     yield loop
#     loop.close()
