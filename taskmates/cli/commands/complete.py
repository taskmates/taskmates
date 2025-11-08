import json

from taskmates.runtimes.cli.cli_completion import CliCompletion
from taskmates.runtimes.cli.cli_context_builder import CliContextBuilder
from taskmates.core.workflow_engine.transaction_manager import runtime


class CompleteCommand:
    help = 'Complete a task'

    def add_arguments(self, parser):
        parser.add_argument('markdown', type=str, nargs='?', help='The markdown to complete')
        parser.add_argument('--history', type=str, help='The history file to read from/save to')
        parser.add_argument('--endpoint', type=str, default=None, help='The Taskmates websocket API endpoint')

        parser.add_argument('--model', type=str, default='claude-sonnet-4-5', help='The model to use')
        parser.add_argument('--workflow', type=str, default='cli_complete', help='The workflow to use')
        parser.add_argument('-n', '--max-steps', type=int, default=100,
                            help='The maximum number of steps')
        parser.add_argument('--inputs', type=json.loads, action='append', default=[],
                            help='JSON string with system prompt template parameters (can be specified multiple times)')
        parser.add_argument('--format', type=str, default='text', choices=['full', 'completion', 'text'],
                            help='Output format')

    async def execute(self, args):
        inputs = CliCompletion.get_args_inputs(args)
        workflow = CliCompletion()
        # We need build_executable_transaction because:
        # 1. It sets up the context from CliContextBuilder (model, max_steps, etc.)
        # 2. It creates the Objective with proper result_format for CLI output
        # 3. It creates an ExecutableTransaction that manages the workflow lifecycle
        # Direct call to fulfill() would use default context from Settings instead
        transaction = runtime.transaction_manager().build_executable_transaction(
            operation=workflow.fulfill.operation,
            outcome=workflow.fulfill.outcome,
            context=CliContextBuilder(args).build(),
            inputs=inputs,
            result_format={'format': args.format or 'completion', 'interactive': False},
            workflow_instance=workflow
        )
        await transaction()
