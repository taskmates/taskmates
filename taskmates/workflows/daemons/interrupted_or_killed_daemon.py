import functools

from taskmates.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.workflow_engine.run import RUN, Run, Objective, ObjectiveKey
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.workflows.contexts.run_context import RunContext


class InterruptedOrKilledDaemon(CompositeContextManager):
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


async def test_interrupted_or_killed(context: RunContext):
    from taskmates.workflows.signals.status_signals import StatusSignals
    from taskmates.workflows.states.interrupted_or_killed import InterruptedOrKilled as InterruptedOrKilledTopic

    # Create a real Run with real signals
    request = Objective(key=ObjectiveKey(outcome="test"))

    # Create a real Run
    run = Run(
        objective=request,
        context=context,
        signals={"status": StatusSignals()},
        state={"interrupted_or_killed": InterruptedOrKilledTopic()},
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
