import functools

from loguru import logger

from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.run import RUN, Run
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.states.interrupted import Interrupted


class InterruptRequestDaemon(Daemon):
    async def handle_interrupt_request(self, _sender, run: Run):
        interrupted = run.state["interrupted"]
        control = run.signals["control"]

        if interrupted.get():
            logger.info("Interrupt requested again. Killing the request.")
            await control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            await control.interrupt.send_async({})
            interrupted.set(True)

    def __enter__(self):
        run = RUN.get()
        control = run.signals["control"]
        self.exit_stack.enter_context(stacked_contexts([
            control.interrupt_request.connected_to(
                functools.partial(self.handle_interrupt_request, run=run))
        ]))


async def test_interrupt_request_mediator():
    from taskmates.workflow_engine.objective import Objective

    # Create a real Run with real signals
    request = Objective(outcome="test")

    # Create a real Run
    run = Run(
        objective=request,
        context={},
        signals={"control": ControlSignals()},
        state={"interrupted": Interrupted()},
        results={},
    )

    # Use context manager to properly initialize the run
    with run:
        mediator = InterruptRequestDaemon()
        with mediator:
            # Track signal emissions
            interrupt_calls = []
            kill_calls = []

            async def interrupt_handler(_):
                interrupt_calls.append(True)

            async def kill_handler(_):
                kill_calls.append(True)

            run.signals["control"].interrupt.connect(interrupt_handler)
            run.signals["control"].kill.connect(kill_handler)

            # Test first interrupt
            await mediator.handle_interrupt_request(None, run)

            assert run.state["interrupted"].get()
            assert len(interrupt_calls) == 1
            assert len(kill_calls) == 0

            # Test second interrupt
            await mediator.handle_interrupt_request(None, run)

            assert run.state["interrupted"].get()
            assert len(interrupt_calls) == 1
            assert len(kill_calls) == 1
