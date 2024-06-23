import logging

import pytest
import pytest_socket
import tiktoken

from taskmates.signals import Signals, SIGNALS
from taskmates.environment.participants.load_participant_config import load_cache

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
    # If the test is marked with 'integration', enable socket connections
    if "integration" in item.keywords:
        pytest_socket.enable_socket()

    # Force the tiktoken encoding to be downloaded before disabling the network
    tiktoken.encoding_for_model("gpt-4")

    pytest_socket.socket_allow_hosts(['127.0.0.1', '::1', 'fe80::1'])


@pytest.fixture
def subject(request):
    return request.getfixturevalue(request.param)



@pytest.fixture(autouse=True)
def reset_cache():
    load_cache.clear()


@pytest.fixture(autouse=True)
def signals():
    stream = Signals()
    SIGNALS.set(stream)
    return stream
