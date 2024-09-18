import json
import os

import select
import sys
from typeguard import typechecked

from taskmates.cli.lib.merge_inputs import merge_inputs
from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.core.workflow_registry import workflow_registry
from taskmates.defaults.workflows.cli_complete import CliComplete


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
        parser.add_argument('--workflow', type=str, default='cli_complete', help='The workflow to use')
        parser.add_argument('-n', '--max-steps', type=int, default=100,
                            help='The maximum number of steps')
        parser.add_argument('--inputs', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args):
        contexts = CliContextBuilder(args).build()

        inputs = merge_inputs(args.inputs)

        stdin_markdown = self.read_stdin_incoming_message()
        args_markdown = await self.get_args_incoming_message(args)
        if stdin_markdown or args_markdown:
            inputs['incoming_messages'] = [stdin_markdown, args_markdown]
        if args.history:
            inputs['history_path'] = args.history
        if args.format:
            inputs['response_format'] = args.format

        if not args.history and not stdin_markdown and not args_markdown and not inputs:
            raise ValueError("No input provided")

        workflow_name = contexts["completion_opts"]["workflow"]
        workflow = workflow_registry[workflow_name](contexts=contexts)
        await workflow.run(**inputs)
        # await CliComplete(contexts).run(**inputs)

    @staticmethod
    async def get_args_incoming_message(args):
        args_markdown = args.markdown
        if args_markdown and not args_markdown.startswith("**"):
            args_markdown = "**user>** " + args_markdown
        return args_markdown

    @typechecked
    def read_stdin_incoming_message(self) -> str:
        # Read markdown from stdin if available
        stdin_markdown = ""
        selected = select.select([sys.stdin, ], [], [], 0.0)[0]
        pycharm_env = os.environ.get("PYCHARM_HOSTED", 0) == '1'
        if (selected or not pycharm_env) and not sys.stdin.isatty():
            stdin_markdown = "".join(sys.stdin.readlines())

        if stdin_markdown and not stdin_markdown.startswith("**"):
            stdin_markdown = "**user>** " + stdin_markdown

        return stdin_markdown
