import json
import os

import sys
from typeguard import typechecked

from taskmates.cli.lib.complete import complete


class CompleteCommand:
    help = 'Complete a task'

    def add_arguments(self, parser):
        parser.add_argument('markdown', type=str, nargs='?', help='The markdown to complete')
        parser.add_argument('--history', type=str, help='The history file to read from/save to')
        parser.add_argument('--endpoint', type=str, default=None, help='The Taskmates websocket API endpoint')

        # parser.add_argument('--input-method', choices=['default', 'websocket'], default='default',
        #                     help='Select input method for control signals')
        # parser.add_argument('--output-method', choices=['default', 'websocket'], default='default',
        #                     help='Select output method for response signals')
        # parser.add_argument('--websocket-url', default='ws://localhost:8765',
        #                     help='WebSocket URL for websocket method')

        parser.add_argument('--model', type=str, default='claude-3-5-sonnet-20240620', help='The model to use')
        parser.add_argument('-n', '--max-interactions', type=int, default=100,
                            help='The maximum number of interactions')
        parser.add_argument('--template-params', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args):
        history = self.read_args_history(args)
        stdin_markdown = self.read_stdin_incoming_message()
        args_markdown = await self.get_args_incoming_message(args)

        if not history and not stdin_markdown and not args_markdown:
            raise ValueError("No input provided")

        await complete(history,
                       [stdin_markdown, args_markdown],
                       args)

    @staticmethod
    async def get_args_incoming_message(args):
        args_markdown = args.markdown
        if args_markdown and not args_markdown.startswith("**"):
            args_markdown = "**user>** " + args_markdown
        return args_markdown

    @staticmethod
    def read_args_history(args):
        history = ""
        if args.history:
            if not os.path.exists(args.history):
                return None
            with open(args.history, 'r') as f:
                history = f.read()
        return history

    @typechecked
    def read_stdin_incoming_message(self) -> str:
        # Read markdown from stdin if available
        stdin_markdown = ""
        pycharm_env = os.environ.get("PYCHARM_HOSTED", 0) == '1'
        if not pycharm_env and not sys.stdin.isatty():
            stdin_markdown = "".join(sys.stdin.readlines())

        if stdin_markdown and not stdin_markdown.startswith("**"):
            stdin_markdown = "**user>** " + stdin_markdown

        return stdin_markdown
