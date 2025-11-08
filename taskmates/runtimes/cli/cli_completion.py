import select
import sys

from typeguard import typechecked

from taskmates.cli.lib.merge_inputs import merge_inputs
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager
from taskmates.runtimes.cli.cli_interrupt_signals_bindings import CliInterruptSignalsBindings
from taskmates.runtimes.cli.get_incoming_markdown import GetIncomingMarkdown
from taskmates.runtimes.cli.history_sink_bindings import HistorySinkBindings
from taskmates.runtimes.cli.signals.history_sink import HistorySink


@typechecked
class CliCompletion:
    @transactional()
    async def fulfill(self,
                      incoming_messages: list = None,
                      history_path: str = None) -> str:

        transaction = runtime.transaction
        history_sink = HistorySink(path=history_path)

        async with ensure_async_context_manager(history_sink), \
                CliInterruptSignalsBindings(transaction):
            # Create child transaction for getting incoming markdown
            get_incoming_markdown_transaction = transaction.create_bound_transaction(
                operation=GetIncomingMarkdown().fulfill,
                inputs={
                    "history_path": history_path,
                    "incoming_messages": incoming_messages
                }
            )

            with HistorySinkBindings(get_incoming_markdown_transaction, history_sink):
                markdown_chat = await get_incoming_markdown_transaction()

            # Create child transaction for markdown completion
            markdown_completion_transaction = transaction.create_bound_transaction(
                operation=MarkdownCompletion().fulfill,
                inputs={"markdown_chat": markdown_chat}
            )

            with HistorySinkBindings(markdown_completion_transaction, history_sink):
                return await markdown_completion_transaction()

    @staticmethod
    def get_args_inputs(args):
        inputs = merge_inputs(args.inputs)
        stdin_markdown = CliCompletion.read_stdin_incoming_message()
        args_markdown = CliCompletion.get_args_incoming_message(args)
        incoming_messages = [stdin_markdown, args_markdown]
        history_path = args.history
        if stdin_markdown or args_markdown:
            inputs['incoming_messages'] = incoming_messages
        if history_path:
            inputs['history_path'] = history_path
        if not history_path and not stdin_markdown and not args_markdown and not inputs:
            raise ValueError("No input provided")
        return inputs

    @staticmethod
    def get_args_incoming_message(args):
        args_markdown = args.markdown
        if args_markdown and not args_markdown.startswith("**"):
            args_markdown = "**user>** " + args_markdown
        return args_markdown

    @staticmethod
    @typechecked
    def read_stdin_incoming_message() -> str:
        # Read markdown from stdin if available
        stdin_markdown = ""
        selected = select.select([sys.stdin, ], [], [], 0)[0]
        if selected:
            stdin_markdown = "".join(sys.stdin.readlines())

        if stdin_markdown and not stdin_markdown.startswith("**"):
            stdin_markdown = "**user>** " + stdin_markdown

        return stdin_markdown
