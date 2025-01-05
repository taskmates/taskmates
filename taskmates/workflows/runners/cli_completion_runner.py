import os
import select
import sys

from typeguard import typechecked

from taskmates.cli.lib.merge_inputs import merge_inputs
from taskmates.workflow_engine.environment import environment
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.run import to_daemons_dict, Objective, ObjectiveKey
from taskmates.workflow_engine.workflow_registry import workflow_registry
from taskmates.workflows.context_builders.cli_context_builder import CliContextBuilder
from taskmates.workflows.signals.sinks.history_sink import HistorySink
from taskmates.workflows.signals.sinks.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
from taskmates.workflows.signals.sources.sig_int_and_sig_term_controller import SigIntAndSigTermController


def read_history(history_path):
    history = ""
    if history_path:
        if not os.path.exists(history_path):
            return None
        with open(history_path, 'r') as f:
            history = f.read()
    return history


class CliCompletionRunner:
    def __init__(self, *,
                 args
                 ):

        self.args = args
        self.context = CliContextBuilder(args).build()

    @typechecked
    async def run(self):
        async def attempt_cli_completion(context):
            with Objective(key=ObjectiveKey(outcome="cli_completion_runner")).environment(context=context) as run:
                await run.signals["status"].start.send_async({})

                inputs = await self.get_args_inputs()

                @environment(fulfillers={
                    'daemons': lambda: to_daemons_dict([
                        SigIntAndSigTermController(),
                        WriteMarkdownChatToStdout(inputs.get('response_format')),
                        HistorySink(inputs.get('history_path'))
                    ])
                })
                async def run_workflow(inputs):
                    workflow_name = self.context["run_opts"]["workflow"]
                    workflow = workflow_registry[workflow_name]()
                    return await workflow.fulfill(**inputs)

                return await run_workflow(inputs)

        return await attempt_cli_completion(self.context)

    @fulfills("args_inputs")
    async def get_args_inputs(self):
        inputs = merge_inputs(self.args.inputs)
        stdin_markdown = self.read_stdin_incoming_message()
        args_markdown = self.get_args_incoming_message(self.args)
        incoming_messages = [stdin_markdown, args_markdown]
        history_path = self.args.history
        response_format = self.args.format
        if stdin_markdown or args_markdown:
            inputs['incoming_messages'] = incoming_messages
        if history_path:
            inputs['history_path'] = history_path
        if response_format:
            inputs['response_format'] = response_format
        if not history_path and not stdin_markdown and not args_markdown and not inputs:
            raise ValueError("No input provided")
        return inputs

    @staticmethod
    def get_args_incoming_message(args):
        args_markdown = args.markdown
        if args_markdown and not args_markdown.startswith("**"):
            args_markdown = "**user>** " + args_markdown
        return args_markdown

    @typechecked
    def read_stdin_incoming_message(self) -> str:
        # Read markdown from stdin if available
        stdin_markdown = ""
        selected = select.select([sys.stdin, ], [], [], 0)[0]
        # if selected or not sys.stdin.isatty():
        if selected:
            stdin_markdown = "".join(sys.stdin.readlines())

        if stdin_markdown and not stdin_markdown.startswith("**"):
            stdin_markdown = "**user>** " + stdin_markdown

        return stdin_markdown
