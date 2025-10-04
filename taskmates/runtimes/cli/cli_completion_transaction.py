import select
import sys

from typeguard import typechecked

from taskmates.cli.lib.merge_inputs import merge_inputs
from taskmates.core.workflow_engine.transaction import Objective, ObjectiveKey, Transaction
from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
from taskmates.lib.contextlib_.stacked_contexts import ensure_async_context_manager
from taskmates.runtimes.cli.cli_context_builder import CliContextBuilder
from taskmates.runtimes.cli.get_incoming_markdown import GetIncomingMarkdown
from taskmates.runtimes.cli.signals.history_sink import HistorySink
from taskmates.runtimes.cli.signals.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.runtimes.cli.signals.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout


async def noop(sender, **kwargs):
    pass


@typechecked
class CliCompletionTransaction(Transaction):
    def __init__(self, *, args):
        # Get inputs from args first
        inputs = self.get_args_inputs(args)

        # TODO: pass format here
        # Initialize parent with objective
        super().__init__(
            objective=Objective(key=ObjectiveKey(
                outcome="CliCompletionTransaction",
                inputs=inputs
            ),
                result_format={'format': args.format or 'completion', 'interactive': False}
            ),
            context=(CliContextBuilder(args).build())
        )

        # Connect status signals to noop handlers
        self.consumes["status"].interrupted.connect(noop)
        self.consumes["status"].killed.connect(noop)

        # Create async context managers after parent initialization
        history_sink = HistorySink(path=self.objective.key['inputs'].get('history_path'))
        self.resources["history_sink"] = history_sink

        self.async_context_managers = list(self.async_context_managers) + [
            ensure_async_context_manager(SigIntAndSigTermController(
                control_signals=self.emits["control"]
            )),
            ensure_async_context_manager(history_sink),
            ensure_async_context_manager(WriteMarkdownChatToStdout(
                execution_environment_signals=self.consumes["execution_environment"],
                input_streams_signals=self.emits["input_streams"],
                format=self.objective.key['inputs'].get('response_format')
            ))
        ]

    async def run(self):
        async with self.async_transaction_context():
            # Create child transaction for getting incoming markdown
            get_incoming_markdown = self.create_child_transaction(
                outcome="GetIncomingMarkdown",
                inputs={
                    "history_path": self.objective.key['inputs'].get('history_path'),
                    "incoming_messages": self.objective.key['inputs']["incoming_messages"]
                },
                transaction_class=GetIncomingMarkdown
            )

            with get_incoming_markdown.consumes["execution_environment"].response.connected_to(
                    self.resources["history_sink"].process_chunk):
                markdown_chat = await get_incoming_markdown.fulfill()

            # Create child transaction for markdown completion
            markdown_completion = self.create_child_transaction(
                outcome="MarkdownCompletion",
                inputs={"markdown_chat": markdown_chat},
                transaction_class=MarkdownCompletion
            )

            with markdown_completion.consumes["execution_environment"].response.connected_to(
                    self.resources["history_sink"].process_chunk):
                return await markdown_completion.fulfill()

    def get_args_inputs(self, args):
        inputs = merge_inputs(args.inputs)
        stdin_markdown = self.read_stdin_incoming_message()
        args_markdown = self.get_args_incoming_message(args)
        incoming_messages = [stdin_markdown, args_markdown]
        history_path = args.history
        response_format = args.format
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
