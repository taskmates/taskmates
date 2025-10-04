import argparse
import json
import sys
from io import StringIO

from taskmates.cli.commands.base import Command
from taskmates.core.workflow_engine.transaction import Objective, ObjectiveKey, Transaction
from taskmates.core.workflows.markdown_completion.build_chat_completion_request import build_chat_completion_request
from taskmates.runtimes.cli.cli_context_builder import CliContextBuilder


class ParseCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument('file', nargs='?', help='Markdown file to parse (reads from stdin if not provided)')

    async def execute(self, args: argparse.Namespace):
        async def attempt_parse_markdown():
            context = CliContextBuilder(args).build()
            async with Transaction(objective=Objective(key=ObjectiveKey(outcome="cli_parse_markdown_runner")),
                                   context=context).async_transaction_context():
                if hasattr(args, 'file') and args.file:
                    with open(args.file, 'r') as f:
                        markdown_chat = f.read()
                else:
                    markdown_chat = "".join(sys.stdin.readlines())

                markdown_path = args.file if hasattr(args, 'file') and args.file else None
                result = build_chat_completion_request(
                    markdown_chat=markdown_chat, 
                    markdown_path=markdown_path,
                    run_opts=context.get("run_opts", {})
                )

                print(json.dumps(result, ensure_ascii=False))

        await attempt_parse_markdown()


async def test_parse(tmp_path):
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
        assert "run_opts" in result

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
