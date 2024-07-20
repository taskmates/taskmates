import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from typeguard import typechecked

from taskmates.cli.lib.complete import complete
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS
from taskmates.config.server_config import ServerConfig, SERVER_CONFIG
from taskmates.signal_config import SignalConfig
from taskmates.signals.signals import Signals, SIGNALS


class CompleteCommand:
    help = 'Complete a task'

    def add_arguments(self, parser):
        parser.add_argument('markdown', type=str, help='The markdown to complete')
        # TODO: commented out because it's not currently implemented
        # parser.add_argument('--output', type=str, help='The output file path')
        parser.add_argument('--endpoint', type=str, default=None,
                            help='The websocket endpoint')
        parser.add_argument('--model', type=str, default='claude-3-5-sonnet-20240620', help='The model to use')
        parser.add_argument('-n', '--max-interactions', type=int, default=100,
                            help='The maximum number of interactions')
        parser.add_argument('--template-params', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'original', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args, signal_config: SignalConfig):
        markdown = self.get_markdown(args)

        request_id = str(uuid4())

        # If --output is not provided, write to request_id file in /var/tmp
        # output = args.output or f"~/.taskmates/completions/{request_id}.md"
        # Path(output).parent.mkdir(parents=True, exist_ok=True)

        context: CompletionContext = {
            "request_id": request_id,
            "markdown_path": str(Path(os.getcwd()) / f"{request_id}.md"),
            "cwd": os.getcwd(),
        }

        server_config: ServerConfig = SERVER_CONFIG.get()

        client_config = ClientConfig(interactive=False,
                                     format=args.format,
                                     endpoint=args.endpoint,
                                     # output=(output if args.output else None)
                                     )

        completion_opts = {
            "model": args.model,
            "template_params": self.merge_template_params(args.template_params),
            "max_interactions": args.max_interactions,
        }

        COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})

        signals = Signals()
        SIGNALS.set(signals)

        await complete(markdown, context,
                       server_config,
                       client_config,
                       completion_opts,
                       signal_config, signals)

    @staticmethod
    def merge_template_params(template_params: list) -> dict:
        merged = {}
        for params in template_params:
            merged.update(params)
        return merged

    @typechecked
    def get_markdown(self, args) -> str:
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
