from typeguard import typechecked

from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager
from taskmates.runtimes.cli.signals.history_sink import HistorySink
from taskmates.runtimes.cli.signals.sig_int_and_sig_term_controller import SigIntAndSigTermController
from taskmates.runtimes.cli.signals.write_markdown_chat_to_stdout import WriteMarkdownChatToStdout


async def noop(sender, **kwargs):
    pass


@typechecked
class CliInterruptSignalsBindings:
    def __init__(self, transaction: Transaction):
        self.transaction = transaction

    async def __aenter__(self):
        # Connect status signals to noop handlers
        self.transaction.consumes["status"].interrupted.connect(noop)
        self.transaction.consumes["status"].killed.connect(noop)

        # Set up daemons that bind transaction signals to resources
        daemons = [
            ensure_async_context_manager(SigIntAndSigTermController(
                control_signals=self.transaction.emits["control"]
            )),
            ensure_async_context_manager(WriteMarkdownChatToStdout(
                execution_environment_signals=self.transaction.consumes["execution_environment"],
                input_streams_signals=self.transaction.emits["input_streams"],
                format=self.transaction.objective.result_format['format']
            ))
        ]

        # Add daemons to transaction's async exit stack
        for daemon in daemons:
            await self.transaction.async_exit_stack.enter_async_context(daemon)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
