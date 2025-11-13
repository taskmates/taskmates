import argparse
import json
import sys
from io import StringIO

from typeguard import typechecked

from taskmates.cli.commands.base import Command
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflow_engine.objective import ObjectiveKey, Objective
from taskmates.core.workflows.markdown_completion.build_completion_request import build_completion_request
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.build_llm_args import \
    build_llm_args
from taskmates.runtimes.cli.cli_context_builder import CliContextBuilder


@typechecked
class ParseCommand(Command):
    def add_arguments(self, parser: argparse.ArgumentParser):
        parser.add_argument('file', nargs='?', help='Markdown file to parse (reads from stdin if not provided)')
        parser.add_argument('--output-format',
                            choices=['completion-request', 'llm-args'],
                            default='completion-request',
                            help='Output format: completion-request (default) or llm-args')

    def read_markdown_chat(self, args: argparse.Namespace) -> str:
        if hasattr(args, 'file') and args.file:
            with open(args.file, 'r') as f:
                markdown_chat = f.read()
        else:
            markdown_chat = "".join(sys.stdin.readlines())
        return markdown_chat

    async def execute(self, args: argparse.Namespace):
        async def attempt_parse_markdown():
            context: RunContext = CliContextBuilder(args).build()
            async with Transaction(objective=Objective(key=ObjectiveKey(outcome="cli_parse_markdown_runner")),
                                   context=context).async_transaction_context():

                markdown_chat = self.read_markdown_chat(args)
                markdown_path = args.file if hasattr(args, 'file') and args.file else None

                completion_request = build_completion_request(
                    markdown_chat=markdown_chat,
                    markdown_path=markdown_path,
                    run_opts=context.get("run_opts", {})
                )

                output_format = getattr(args, 'output_format', 'completion-request')

                if output_format == 'llm-args':
                    inputs = completion_request["run_opts"].get("inputs", {})
                    llm_args = build_llm_args(
                        messages=completion_request["messages"],
                        available_tools=completion_request["available_tools"],
                        participants=completion_request["participants"],
                        inputs=inputs,
                        model_conf={},
                        client=None
                    )

                    # Convert LangChain objects to serializable format
                    serializable_result = {
                        'messages': [
                            {
                                'type': msg.__class__.__name__,
                                'content': msg.content,
                                'tool_calls': [
                                    {
                                        'id': tc.get('id'),
                                        'type': tc.get('type'),
                                        'name': tc.get('name'),
                                        'args': tc.get('args')
                                    } for tc in getattr(msg, 'tool_calls', [])
                                ] if hasattr(msg, 'tool_calls') and msg.tool_calls else [],
                                'tool_call_id': getattr(msg, 'tool_call_id', None)
                            } for msg in llm_args['messages']
                        ],
                        'tools': [
                            {
                                'name': tool.name,
                                'description': tool.description,
                                'args_schema': tool.args_schema.schema() if hasattr(tool.args_schema,
                                                                                    'schema') else str(tool.args_schema)
                            } for tool in llm_args['tools']
                        ],
                        'model_params': llm_args['model_params']
                    }
                    print(json.dumps(serializable_result, ensure_ascii=False))
                else:
                    print(json.dumps(completion_request, ensure_ascii=False))

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
        args = argparse.Namespace(taskmates_dir=str(taskmates_dir), output_format='completion-request')
        await command.execute(args)

        # Get the output
        output = sys.stdout.getvalue()
        result = json.loads(output)

        assert result == {'available_tools': [],
                          'messages': [{'content': 'Hello\n\n',
                                        'name': 'user',
                                        'recipient': 'assistant',
                                        'recipient_role': 'assistant',
                                        'role': 'user'},
                                       {'content': 'Hi there!',
                                        'name': 'assistant',
                                        'recipient': 'user',
                                        'recipient_role': 'user',
                                        'role': 'assistant'}],
                          'participants': {'assistant': {'name': 'assistant', 'role': 'assistant'},
                                           'user': {'name': 'user', 'role': 'user'}},
                          'run_opts': {'max_steps': 2, 'model': 'quote'}}

    finally:
        # Restore stdin and stdout
        sys.stdin, sys.stdout = old_stdin, old_stdout


async def test_parse_with_llm_args_format(tmp_path):
    # Prepare test input
    test_input = "**user>** Hello\n\n"

    # Create a temporary taskmates directory
    taskmates_dir = tmp_path / "taskmates"
    taskmates_dir.mkdir()

    # Redirect stdin and stdout
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = StringIO(test_input)
    sys.stdout = StringIO()

    try:
        # Create and execute the command with llm-args format
        command = ParseCommand()
        args = argparse.Namespace(taskmates_dir=str(taskmates_dir), output_format='llm-args')
        await command.execute(args)

        # Get the output
        output = sys.stdout.getvalue()
        result = json.loads(output)

        assert result == {'messages': [{'content': 'Hello\n\n',
                                        'tool_call_id': None,
                                        'tool_calls': [],
                                        'type': 'HumanMessage'}],
                          'model_params': {},
                          'tools': []}

    finally:
        # Restore stdin and stdout
        sys.stdin, sys.stdout = old_stdin, old_stdout
