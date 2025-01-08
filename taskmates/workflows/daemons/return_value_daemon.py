import functools

from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.run import RUN, Run, Objective, ObjectiveKey
from taskmates.workflows.contexts.run_context import RunContext
from taskmates.workflows.signals.status_signals import StatusSignals


class ReturnValueDaemon(Daemon):
    async def handle_stdout_chunk(self, chunk: str, run: Run):
        run.state["return_value"].append_stdout_chunk(chunk)

    async def handle_return_value(self, value, run: Run):
        run.state["return_value"].set_return_value(value)

    async def handle_error(self, error: Exception, run: Run):
        run.state["return_value"].set_error(error)

    def __enter__(self):
        run = RUN.get()
        self.exit_stack.enter_context(stacked_contexts([
            run.signals["status"].success.connected_to(
                functools.partial(self.handle_return_value, run=run))
        ]))


async def test_return_value(context: RunContext):
    from taskmates.workflows.states.return_value import ReturnValue as ReturnValueTopic

    # Create a real Run with real signals
    request = Objective(key=ObjectiveKey(outcome="test"))

    # Create a real Run
    run = Run(
        objective=request,
        context=context,
        signals={"status": StatusSignals()},
        state={"return_value": ReturnValueTopic()}
    )

    # Use context manager to properly initialize the run
    with run:
        daemon = ReturnValueDaemon()
        with daemon:
            # Test return value
            test_value = {"key": "value"}
            await run.signals["status"].success.send_async(test_value)
            assert run.state["return_value"].get_return_value() == test_value
