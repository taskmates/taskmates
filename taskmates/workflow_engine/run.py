import contextvars
from typing import Any, Generic, TypeVar, Mapping

from blinker import Namespace, Signal
from opentelemetry import trace
from ordered_set import OrderedSet
from typeguard import typechecked

from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.workflow_engine.base_signals import BaseSignals
from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.runner import Runner

Signal.set_class = OrderedSet

TContext = TypeVar('TContext', bound=Mapping)


@typechecked
class Run(Generic[TContext], Daemon):
    def __init__(self,
                 objective: Objective,
                 context: TContext,
                 signals: dict[str, BaseSignals],
                 state: dict[str, Any],
                 results: dict[str, Any],
                 daemons: dict[str, Daemon] | list[Daemon] | None = None,
                 ):
        super().__init__()
        self.namespace = Namespace()

        self.objective = objective

        self.context: TContext = context
        self.signals = signals
        self.daemons = to_daemons_dict(daemons)
        self.state = state

        self.results = results
        # TODO: self.actions =

    # def _add_state(self, name: str, value):
    #     if name in self.state:
    #         raise ValueError(f"State '{name}' is already registered")
    #     self.state[name] = value

    def request(self, outcome: str | None = None, inputs: dict | None = None) -> Objective:
        return Objective(outcome=outcome,
                         inputs=inputs,
                         requester=self)

    def __enter__(self):
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(RUN, self))

        # Enters the context of all daemons
        self.exit_stack.enter_context(stacked_contexts(list(self.daemons.values())))

        return self

    def __repr__(self):
        return f"{self.__class__.__name__}(outcome={self.objective.outcome})"

    def set_result(self, outcome: str, args_key: dict | None, result: Any):
        if args_key is None:
            self.results[outcome] = result
        else:
            if outcome not in self.results:
                self.results[outcome] = {}
            self.results[outcome][str(args_key)] = result

    def get_result(self, outcome: str, args_key: dict | None) -> Any | None:
        if outcome not in self.results:
            return None

        if isinstance(self.results[outcome], dict):
            return self.results[outcome].get(str(args_key))

        return self.results[outcome]

    async def run_steps(self, steps):
        self.objective.runs.append(self)

        runner = Runner(func=steps, inputs=self.objective.inputs)

        with tracer().start_as_current_span(
                format_span_name(steps, self.objective),
                kind=trace.SpanKind.INTERNAL
        ):
            with self:
                runner.start()
                return await runner.get_result()


RUN: contextvars.ContextVar[Run] = contextvars.ContextVar(Run.__class__.__name__)


def to_daemons_dict(jobs):
    if jobs is None:
        return {}
    if isinstance(jobs, Run):
        return to_daemons_dict([jobs])
    if isinstance(jobs, dict):
        return jobs
    if isinstance(jobs, list):
        return {to_snake_case(job.__class__.__name__): job for job in jobs}
