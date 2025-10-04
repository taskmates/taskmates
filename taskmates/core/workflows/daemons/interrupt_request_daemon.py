from loguru import logger

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.states.interrupt_state import InterruptState
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class InterruptRequestDaemon(CompositeContextManager):
    def __init__(self, control_signals: ControlSignals, interrupt_state: InterruptState):
        super().__init__()
        self.control_signals = control_signals
        self.interrupt_state = interrupt_state

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_state.value == "interrupting":
            logger.info("Interrupt requested again. Killing the request.")
            self.interrupt_state.value = "killed"
            await self.control_signals.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            self.interrupt_state.value = "interrupting"
            await self.control_signals.interrupt.send_async({})

    def __enter__(self):
        self.exit_stack.enter_context(stacked_contexts([
            self.control_signals.interrupt_request.connected_to(self.handle_interrupt_request)]))


async def test_interrupt_request_mediator():
    # Create control signals and interrupt state
    control_signals = ControlSignals(name="test-control-signals")
    interrupt_state = InterruptState()

    mediator = InterruptRequestDaemon(control_signals, interrupt_state)
    with mediator:
        # Track signal emissions
        interrupt_calls = []
        kill_calls = []

        async def interrupt_handler(_):
            interrupt_calls.append(True)

        async def kill_handler(_):
            kill_calls.append(True)

        control_signals.interrupt.connect(interrupt_handler)
        control_signals.kill.connect(kill_handler)

        # Test first interrupt
        await mediator.handle_interrupt_request(None)

        assert interrupt_state.value == "interrupting"
        assert len(interrupt_calls) == 1
        assert len(kill_calls) == 0

        # Test second interrupt
        await mediator.handle_interrupt_request(None)

        assert interrupt_state.value == "killed"
        assert len(interrupt_calls) == 1
        assert len(kill_calls) == 1
