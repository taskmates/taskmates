import json
import os
import sys

from typeguard import typechecked

from taskmates.cli.lib.complete import complete
from taskmates.signal_config import SignalConfig, SignalMethod


class CompleteCommand:
    help = 'Complete a task'

    def add_arguments(self, parser):
        parser.add_argument('markdown', type=str, help='The markdown to complete')
        parser.add_argument('--endpoint', type=str, default=None,
                            help='The websocket endpoint')
        parser.add_argument('--model', type=str, default='claude-3-5-sonnet-20240620', help='The model to use')
        parser.add_argument('-n', '--max-interactions', type=int, default=100,
                            help='The maximum number of interactions')
        parser.add_argument('--template-params', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'original', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args):
        signal_config = SignalConfig(
            input_method=SignalMethod(args.input_method),
            output_method=SignalMethod(args.output_method),
            websocket_url=args.websocket_url
        )

        markdown = self.compose_input_markdown(args)
        await complete(markdown, args, signal_config)

    @typechecked
    def compose_input_markdown(self, args) -> str:
        # Read markdown from stdin if available
        stdin_markdown = ""
        pycharm_env = os.environ.get("PYCHARM_HOSTED", 0) == '1'
        if not pycharm_env and not sys.stdin.isatty():
            stdin_markdown = "".join(sys.stdin.readlines())
        args_markdown = args.markdown

        if stdin_markdown and args_markdown:
            # Concatenate stdin markdown with --markdown argument if both are provided
            # TODO: Not sure about this being hardcoded to user
            markdown = stdin_markdown + "\n\n**user>** " + args_markdown
        elif stdin_markdown:
            markdown = stdin_markdown
        elif args_markdown:
            markdown = args_markdown
        else:
            raise ValueError("No markdown provided")
        return markdown
