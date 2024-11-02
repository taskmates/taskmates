import json

from taskmates.workflows.runners.cli_completion_runner import CliCompletionRunner


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

        parser.add_argument('--model', type=str, default='claude-3-5-sonnet-20241022', help='The model to use')
        parser.add_argument('--workflow', type=str, default='cli_complete', help='The workflow to use')
        parser.add_argument('-n', '--max-steps', type=int, default=100,
                            help='The maximum number of steps')
        parser.add_argument('--inputs', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args):
        await CliCompletionRunner(args=args).run()
