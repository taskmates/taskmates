import logging

import pytest
import pytest_socket
import tiktoken
from dotenv import load_dotenv

from taskmates.config.load_participant_config import load_cache
from taskmates.core.code_execution.code_cells.execute_markdown_on_local_kernel import kernel_pool
from taskmates.sdk.extension_manager import EXTENSION_MANAGER
from taskmates.signals.signals import Signals, SIGNALS

load_dotenv('.env.test', override=True)
load_dotenv('.env.test.local', override=True)


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
        pytest_socket.enable_socket()
    else:
        pytest_socket.socket_allow_hosts(['127.0.0.1', '::1', 'fe80::1'])


@pytest.fixture
def subject(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(autouse=True)
def reset_cache():
    load_cache.clear()


@pytest.fixture(autouse=True)
def extension_manager():
    EXTENSION_MANAGER.get().initialize()
    return EXTENSION_MANAGER.get()


@pytest.fixture(autouse=True)
def signals():
    stream = Signals()
    SIGNALS.set(stream)
    return stream


@pytest.fixture(scope="function", autouse=True)
async def teardown_after_all_tests():
    yield

    for path, kernel in kernel_pool.items():
        kernel.shutdown_kernel(now=True)
    kernel_pool.clear()
