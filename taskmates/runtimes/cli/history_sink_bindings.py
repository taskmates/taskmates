from typeguard import typechecked

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.runtimes.cli.signals.history_sink import HistorySink


@typechecked
class HistorySinkBindings(CompositeContextManager):
    def __init__(self, transaction: Transaction, history_sink: HistorySink):
        super().__init__()
        self.transaction = transaction
        self.history_sink =  history_sink

    def __enter__(self):
        connection = self.transaction.consumes["execution_environment"].response.connected_to(
            self.history_sink.process_chunk
        )
        self.exit_stack.enter_context(connection)
        return self
