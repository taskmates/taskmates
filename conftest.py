import logging
import os

import pytest
import pytest_socket
import tiktoken
from dotenv import load_dotenv

from taskmates.config.load_participant_config import load_cache
from taskmates.context_builders.test_context_builder import TestContextBuilder
from taskmates.contexts import CONTEXTS
from taskmates.core.code_execution.code_cells.execute_markdown_on_local_kernel import kernel_pool
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.root_path.root_path import root_path
from taskmates.signals.signals import Signals, SIGNALS
from taskmates.taskmates_runtime import TASKMATES_RUNTIME


def pytest_configure(config):
    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Ensure the logger has at least one handler.
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)


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
    load_dotenv(root_path() / f'.env.{env}', override=True)
    load_dotenv(root_path() / f'.env.{env}.local', override=True)


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


@pytest.fixture(autouse=True)
def signals(taskmates_runtime):
    stream = Signals()
    SIGNALS.set(stream)
    return stream


@pytest.fixture(autouse=True)
def contexts(taskmates_runtime, tmp_path):
    contexts = TestContextBuilder(tmp_path).build()
    with temp_context(CONTEXTS, contexts):
        yield contexts


@pytest.fixture(scope="function", autouse=True)
async def teardown_after_all_tests(taskmates_runtime):
    yield

    for path, kernel in kernel_pool.items():
        kernel.shutdown_kernel(now=True)
    kernel_pool.clear()
