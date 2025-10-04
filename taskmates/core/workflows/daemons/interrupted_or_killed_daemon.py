from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.interrupt_state import InterruptState
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class InterruptedOrKilledDaemon(CompositeContextManager):
    def __init__(self, status_signals: StatusSignals, interrupt_state: InterruptState):
        super().__init__()
        self.status_signals = status_signals
        self.interrupt_state = interrupt_state

    async def handle_interrupted(self, _sender):
        self.interrupt_state.value = "interrupted"

    async def handle_killed(self, _sender):
        self.interrupt_state.value = "killed"

    def __enter__(self):
        self.exit_stack.enter_context(stacked_contexts([
            self.status_signals.interrupted.connected_to(self.handle_interrupted),
            self.status_signals.killed.connected_to(self.handle_killed)]))


async def test_interrupted_or_killed():
    # Create status signals and interrupt state
    status_signals = StatusSignals(name="test-status-signals")
    interrupt_state = InterruptState()

    # Use context manager to properly initialize the run
    daemon = InterruptedOrKilledDaemon(status_signals, interrupt_state)
    with daemon:
        # Test interruption
        await status_signals.interrupted.send_async({})
        assert interrupt_state.value == "interrupted"

        # Reset and test killed
        interrupt_state.value = None
        await status_signals.killed.send_async({})
        assert interrupt_state.value == "killed"
