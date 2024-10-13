import os
import select
import sys

from typeguard import typechecked

from taskmates.cli.lib.merge_inputs import merge_inputs
from taskmates.context_builders.cli_context_builder import CliContextBuilder
from taskmates.core.io.emitters.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.core.io.listeners.history_sink import HistorySink
from taskmates.core.io.listeners.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout
from taskmates.core.run import Run, jobs_to_dict
from taskmates.core.workflow_registry import workflow_registry


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
        self.contexts = CliContextBuilder(args).build()

    @typechecked
    async def run(self):

        inputs = merge_inputs(self.args.inputs)

        stdin_markdown = self.read_stdin_incoming_message()
        args_markdown = await self.get_args_incoming_message(self.args)
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

        jobs = jobs_to_dict([
            SigIntAndSigTermController(),
            WriteMarkdownChatToStdout(response_format),
            HistorySink(history_path)
        ])

        # TODO: build a new RunnerContext object here
        with Run(jobs=jobs):
            workflow_name = self.contexts["run_opts"]["workflow"]
            workflow = workflow_registry[workflow_name](contexts=self.contexts)
            result = await workflow.run(**inputs)
            # result = await CliComplete(contexts=self.contexts).run(**inputs)

        return result

        # try:
        # # TODO: move this to EXECUTION_ENVIRONMENT
        # except Exception as e:
        #     signals = RUN.get()
        #     await signals.output_streams.error.send_async(e)
        #     raise e
        #     logger.error(e)

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
