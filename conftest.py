import os

import pytest
import pytest_socket
import tiktoken

from taskmates.config.load_participant_config import load_cache
from taskmates.core.actions.code_execution.code_cells.execute_markdown_on_local_kernel import kernel_pool
from taskmates.load_env_files import load_env_for_environment
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.run import Run
from taskmates.workflows.context_builders.test_context_builder import TestContextBuilder
from taskmates.workflows.daemons.captured_signals_daemon import CapturedSignalsDaemon
from taskmates.workflows.signals.sinks.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
from taskmates.workflows.states.captured_signals import CapturedSignals


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
def run_opts():
    return {
        "model": "quote",
        "max_steps": 1
    }


@pytest.fixture
def context(request, taskmates_runtime, run_opts, tmp_path):
    context = TestContextBuilder(tmp_path).build(run_opts)

    if "integration" in request.node.keywords:
        context["run_opts"]["model"] = "claude-3-5-sonnet-20241022"
        context["run_opts"]["max_steps"] = 100
    else:
        context["run_opts"]["model"] = "quote"
        context["run_opts"]["max_steps"] = 1

    return context


@pytest.fixture
def daemons(request):
    if "integration" in request.node.keywords:
        return [WriteMarkdownChatToStdout("full")]
    else:
        return [CapturedSignalsDaemon()]


@pytest.fixture(autouse=True)
def run(request, taskmates_runtime, context, daemons):
    with Run(objective=Objective(outcome=request.node.name),
             context=context,
             daemons=daemons,
             signals=default_environment_signals(),
             state={"captured_signals": CapturedSignals()},
             results={}) as run:
        yield run


@pytest.fixture(scope="function", autouse=True)
async def teardown_after_all_tests(taskmates_runtime):
    yield

    for path, kernel in kernel_pool.items():
        kernel.shutdown_kernel(now=True)
    kernel_pool.clear()
