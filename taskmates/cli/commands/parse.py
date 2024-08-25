import argparse
import json
import os
from io import StringIO

import pytest
import sys

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.cli.commands.base import Command
from taskmates.contexts import build_default_contexts
from taskmates.sdk.extension_manager import EXTENSION_MANAGER


class ParseCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        pass  # No additional arguments needed for parse command

    async def execute(self, args: argparse.Namespace):
        contexts = build_default_contexts()
        contexts["completion_context"]["cwd"] = os.getcwd()

        EXTENSION_MANAGER.get().after_build_contexts(contexts)

        taskmates_dirs = contexts["client_config"]["taskmates_dirs"]
        markdown_chat = "".join(sys.stdin.readlines())
        result = await parse_markdown_chat(markdown_chat, None, taskmates_dirs)
        print(json.dumps(result, ensure_ascii=False))


@pytest.mark.asyncio
async def test_parse_command_execute(tmp_path):
    # Prepare test input
    test_input = "**user>** Hello\n\n**assistant>** Hi there!"

    # Create a temporary taskmates directory
    taskmates_dir = tmp_path / "taskmates"
    taskmates_dir.mkdir()

    # Redirect stdin and stdout
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = StringIO(test_input)
    sys.stdout = StringIO()

    try:
        # Create and execute the command
        command = ParseCommand()
        args = argparse.Namespace(taskmates_dir=str(taskmates_dir))
        await command.execute(args)

        # Get the output
        output = sys.stdout.getvalue()
        result = json.loads(output)

        # Assertions
        assert "participants" in result
        assert "messages" in result
        assert "available_tools" in result
        assert "completion_opts" in result

        # Check messages
        assert len(result["messages"]) == 3  # system message + user message + assistant message

        # Check system message
        assert result["messages"][0]["role"] == "system"
        assert "Your username is `user`" in result["messages"][0]["content"]

        # Check for user and assistant messages
        non_system_messages = [msg for msg in result["messages"] if msg["role"] != "system"]
        assert len(non_system_messages) == 2, "Expected two non-system messages"

        # Check that we have both "Hello" and "Hi there!" messages
        message_contents = [msg["content"].strip() for msg in non_system_messages]
        assert "Hello" in message_contents, "User message 'Hello' not found"
        assert "Hi there!" in message_contents, "Assistant message 'Hi there!' not found"

        # Check that we have both user and assistant roles
        message_roles = [msg["role"] for msg in non_system_messages]
        assert "user" in message_roles, "User role not found"
        assert "assistant" in message_roles, "Assistant role not found"

        # Check recipients
        assert any(msg["recipient"] == "assistant" for msg in
                   non_system_messages), "Message with recipient 'assistant' not found"
        assert any(msg["recipient"] == "user" for msg in non_system_messages), "Message with recipient 'user' not found"

        # Check participants
        assert "user" in result["participants"]
        assert "assistant" in result["participants"]

    finally:
        # Restore stdin and stdout
        sys.stdin, sys.stdout = old_stdin, old_stdout
