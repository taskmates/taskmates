import pytest

from taskmates import root_path
from taskmates.docker.dev_environment import DevEnvironment


@pytest.fixture
def dev_env():
    compose_file = root_path() / ".devcontainer/docker-compose.yml"

    env = DevEnvironment(
        compose_files=compose_file,
        project_name="test_taskmates",
        project_directory=root_path()
    )

    try:
        env.up()
        yield env
    finally:
        env.destroy()


def test_repository_mount(dev_env):
    result = dev_env.execute(
        command=["sh", "-c", "git rev-parse --is-inside-work-tree && echo 'mounted' || echo 'not mounted'"],
        workdir="/host/repository"
    )
    assert "mounted" in result.lower()


def test_taskmates_version(dev_env):
    result = dev_env.execute(
        command=["taskmates", "--version"]
    )

    assert result == "Taskmates 0.2.0"


def test_anthropic_api_key(dev_env):
    result = dev_env.execute(
        command=["sh", "-c", "echo $ANTHROPIC_API_KEY | wc -c"]
    )
    # Convert result to int and verify it's greater than 1 (meaning not empty)
    assert int(result.strip()) > 1


@pytest.mark.integration
def test_taskmates_completion(dev_env):
    result = dev_env.execute(
        command=["sh", "-c", "taskmates complete --model echo 'Hello'"])

    assert result == "Hello\n"
