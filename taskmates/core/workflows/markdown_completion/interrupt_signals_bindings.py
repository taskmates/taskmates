from typeguard import typechecked

from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.core.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.core.workflows.states.interrupt_state import InterruptState
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager


@typechecked
class InterruptSignalsBindings:
    def __init__(self, transaction: Transaction, state: InterruptState):
        self.transaction = transaction
        self.state = state

    async def __aenter__(self):
        daemons = [
            ensure_async_context_manager(InterruptRequestDaemon(
                self.transaction.emits["control"],
                self.state)),
            ensure_async_context_manager(InterruptedOrKilledDaemon(
                self.transaction.consumes["status"],
                self.state))
        ]

        # Add daemons to transaction's async exit stack
        for daemon in daemons:
            await self.transaction.async_exit_stack.enter_async_context(daemon)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup is handled by transaction.async_exit_stack
        pass
