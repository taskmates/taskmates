import json
import os
from pathlib import Path
from uuid import uuid4

from taskmates.cli.lib.complete import complete
from taskmates.config import CompletionContext, ClientConfig, ServerConfig, COMPLETION_OPTS
from taskmates.signal_config import SignalConfig
from taskmates.signals.signals import Signals, SIGNALS


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

    async def execute(self, args, signal_config: SignalConfig):
        markdown = args.markdown

        request_id = str(uuid4())

        context: CompletionContext = {
            "request_id": request_id,
            "markdown_path": str(Path(os.getcwd()) / f"{request_id}.md"),
            "cwd": os.getcwd(),
        }

        client_config = ClientConfig(interactive=False,
                                     format=args.format,
                                     endpoint=args.endpoint)

        completion_opts = {
            "model": args.model,
            "template_params": self.merge_template_params(args.template_params),
            "max_interactions": args.max_interactions,
        }

        COMPLETION_OPTS.set({**COMPLETION_OPTS.get(), **completion_opts})

        signals = Signals()
        SIGNALS.set(signals)

        try:
            await complete(markdown, context, client_config, completion_opts, signal_config, signals)
        finally:
            pass  # The bridges are now handled within the complete function

    @staticmethod
    def merge_template_params(template_params: list) -> dict:
        merged = {}
        for params in template_params:
            merged.update(params)
        return merged
