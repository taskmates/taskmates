import argparse
import json
import sys
from taskmates.cli.commands.base import Command
from taskmates.actions.parse_markdown_chat import parse_markdown_chat

class ParseCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        pass  # No additional arguments needed for parse command

    async def execute(self, args: argparse.Namespace):
        markdown_chat = "".join(sys.stdin.readlines())
        result = await parse_markdown_chat(markdown_chat, None)
        print(json.dumps(result, ensure_ascii=False))
