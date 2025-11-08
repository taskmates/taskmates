import json
import os
import subprocess
import textwrap

import pytest


@pytest.fixture
def cli_runner(tmp_path):
    def run_cli_command(args, input_data=None):
        cmd = ["taskmates"] + args
        taskmates_home = tmp_path / ".taskmates"
        env = os.environ.copy()
        env["TASKMATES_HOME"] = str(taskmates_home)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(tmp_path),
            env=env
        )
        stdout, stderr = process.communicate(input=input_data)
        return stdout, stderr, process.returncode

    return run_cli_command


def test_parse_basic(cli_runner):
    input_data = textwrap.dedent("""
    **user>** Hello

    **assistant>** Hi there!
    """)

    args = ["parse"]
    stdout, stderr, returncode = cli_runner(args, input_data)

    assert returncode == 0
    assert not stderr

    result = json.loads(stdout)

    assert "participants" in result
    assert "messages" in result
    assert "available_tools" in result
    assert "run_opts" in result

    # No system message in CompletionRequest (it's added in build_llm_args)
    assert len(result["messages"]) == 3  # empty message + user message + assistant message

    non_system_messages = result["messages"]
    assert len(non_system_messages) == 3

    message_contents = [msg["content"].strip() for msg in non_system_messages if msg["content"].strip()]
    assert "Hello" in message_contents
    assert "Hi there!" in message_contents

    message_roles = [msg["role"] for msg in non_system_messages if msg["content"].strip()]
    assert "user" in message_roles
    assert "assistant" in message_roles

    assert any(msg["recipient"] == "assistant" for msg in non_system_messages if msg["content"].strip())
    assert any(msg["recipient"] == "user" for msg in non_system_messages if msg["content"].strip())

    assert "user" in result["participants"]
    assert "assistant" in result["participants"]


def test_parse_with_mention(cli_runner, tmp_path):
    taskmates_home = tmp_path / ".taskmates"
    (taskmates_home / "taskmates").mkdir(parents=True)
    (taskmates_home / "taskmates" / "jeff.md").write_text("You're a helpful assistant named Jeff\n")

    input_data = textwrap.dedent("""\
    **user>** Hey @jeff, how are you?
    """)

    args = ["parse"]
    stdout, stderr, returncode = cli_runner(args, input_data)

    assert returncode == 0
    assert not stderr

    result = json.loads(stdout)

    # No system message in CompletionRequest (it's added in build_llm_args)
    assert len(result["messages"]) == 1

    assert result["messages"][-1]["recipient"] == "jeff"
    assert result["messages"][-1]["recipient_role"] == "assistant"

# TODO: we should raise an error instead
# def test_parse_empty_input(cli_runner):
#     input_data = ""
#
#     args = ["parse"]
#     stdout, stderr, returncode = cli_runner(args, input_data)
#
#     assert returncode == 0
#     assert not stderr
#
#     result = json.loads(stdout)
#
#     assert "participants" in result
#     assert "messages" in result
#     assert "available_tools" in result
#     assert "run_opts" in result
#
#     assert len(result["messages"]) == 1  # only user message (empty)
#     assert result["messages"][0]["role"] == "user"
#     assert result["messages"][0]["content"] == ""
