from typing import Any

from typeguard import typechecked

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflows.contexts.context import Context
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.input_streams import InputStreams
from taskmates.workflows.signals.output_streams import OutputStreams
from taskmates.workflows.signals.status_signals import StatusSignals


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

    def attempt(self,
                context: Context | None = None,
                daemons: dict[str, Daemon] | list[Daemon] | None = None,
                state: dict[str, Any] | None = None,
                signals: dict[str, Any] | None = None
                ):
        from taskmates.workflow_engine.run import Run

        if state is None:
            state = {}

        if signals is None:
            signals = {}

        if self.requester is None:
            root_signals = {
                'control': ControlSignals(),
                'status': StatusSignals(),
                'input_streams': InputStreams(),
                'output_streams': OutputStreams()
            }
            signals = {**root_signals, **signals}
            state = state
            results = {}
            if context is None:
                raise ValueError("Runner context is required when requester is not provided")
        else:
            context = self.requester.context
            signals = {**self.requester.signals, **signals}
            state = {**self.requester.state, **state}
            results = self.requester.results

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
