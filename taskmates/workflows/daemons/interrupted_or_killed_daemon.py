import functools

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.run import RUN, Run
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class InterruptedOrKilledDaemon(Daemon):
    async def handle_interrupted(self, _sender, run: Run):
        run.state["interrupted_or_killed"].set(True)

    async def handle_killed(self, _sender, run: Run):
        run.state["interrupted_or_killed"].set(True)

    def __enter__(self):
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.signals["status"].interrupted.connected_to(
                functools.partial(self.handle_interrupted, run=run)),
            run.signals["status"].killed.connected_to(
                functools.partial(self.handle_killed, run=run))
        ]))


async def test_interrupted_or_killed():
    from taskmates.workflow_engine.objective import Objective
    from taskmates.workflows.signals.status_signals import StatusSignals
    from taskmates.workflows.states.interrupted_or_killed import InterruptedOrKilled as InterruptedOrKilledTopic

    # Create a real Run with real signals
    request = Objective(outcome="test")

    # Create a real Run
    run = Run(
        objective=request,
        context={},
        signals={"status": StatusSignals()},
        state={"interrupted_or_killed": InterruptedOrKilledTopic()},
        results={},
    )

    # Use context manager to properly initialize the run
    with run:
        daemon = InterruptedOrKilledDaemon()
        with daemon:
            # Test interruption
            await run.signals["status"].interrupted.send_async({})
            assert run.state["interrupted_or_killed"].get() is True

            # Reset and test killed
            run.state["interrupted_or_killed"].set(False)
            await run.signals["status"].killed.send_async({})
            assert run.state["interrupted_or_killed"].get() is True
