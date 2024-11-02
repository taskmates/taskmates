from typing import Any

from typeguard import typechecked

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.workflows.contexts.context import Context


@typechecked
class Objective:
    def __init__(self, *,
                 outcome: str | None = None,
                 inputs: dict | None = None,
                 requester=None
                 ):
        self.outcome = outcome
        self.inputs = inputs or {}
        self.requester = requester

        self.runs = []
        self.last_run = None

    def environment(self, context: Context):
        from taskmates.workflow_engine.run import Run

        return Run(
            objective=self,
            context=context,
            daemons={},
            signals=default_environment_signals(),
            state={},
            results={}
        )

    def attempt(self,
                context: Context | None = None,
                daemons: dict[str, Daemon] | list[Daemon] | None = None,
                state: dict[str, Any] | None = None,
                signals: dict[str, Any] | None = None,
                results: dict[str, Any] | None = None
                ):
        from taskmates.workflow_engine.run import Run

        if state is None:
            state = {}

        if signals is None:
            signals = {}

        context = self.requester.context
        signals = {**self.requester.signals, **signals}
        state = {**self.requester.state, **state}
        results = results or self.requester.results

        return Run(
            objective=self,
            context=context,
            daemons=daemons,
            signals=signals,
            state=state,
            results=results
        )

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.outcome}>"
