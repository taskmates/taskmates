import contextlib
import contextvars
import copy
import functools
from contextlib import AbstractContextManager

from blinker import Namespace, Signal
from opentelemetry import trace
from ordered_set import OrderedSet

from taskmates.core.signals.artifact_signals import ArtifactSignals
from taskmates.core.signals.control_signals import ControlSignals
from taskmates.core.signals.inputs_signals import InputsSignals
from taskmates.core.signals.outputs_signals import OutputsSignals
from taskmates.core.signals.status_signals import StatusSignals
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.runner.contexts.contexts import Contexts
from taskmates.taskmates_runtime import TASKMATES_RUNTIME

Signal.set_class = OrderedSet


class ExecutionContext(AbstractContextManager):
    def __init__(self,
                 # TODO: name
                 name: str = None,
                 contexts: Contexts = None,
                 jobs: dict[str, 'ExecutionContext'] | list['ExecutionContext'] = None,
                 ):
        self.namespace = Namespace()
        self.parent: ExecutionContext = EXECUTION_CONTEXT.get(None)
        self.exit_stack = contextlib.ExitStack()

        if name is None:
            name = to_snake_case(self.__class__.__name__) if self.parent else "root"
        self.name = name

        self.contexts: Contexts = copy.deepcopy(coalesce(contexts, getattr(self.parent, 'contexts', {})))

        # TODO: Move to writer

        # TODO: Move to Interrupt*
        self.control = getattr(self.parent, 'control', ControlSignals())
        self.status = getattr(self.parent, 'status', StatusSignals())

        # TODO: Move to CurrentMarkdown
        # - how about history?
        #   - markdown writes, signal reads
        self.inputs = getattr(self.parent, 'inputs', InputsSignals())
        self.outputs = getattr(self.parent, 'outputs', OutputsSignals())

        self.artifact = getattr(self.parent, 'artifacts', ArtifactSignals())

        # ---

        self.workflow_inputs = {}

        self.jobs = jobs_to_dict(jobs)
        self.jobs_registry = getattr(self.parent, 'jobs_registry', {})
        self.jobs_registry[self.name] = self
        self.jobs_registry.update(self.jobs)

        # TODO: local vs inherited context
        # self.inputs: dict = {}
        # self.outputs: dict = {}

    # def assign_context(self, value, parent_value, deep_copy=False):
    #     if value is not None:
    #         return value
    #     elif parent_value is not None:
    #         return copy.deepcopy(parent_value) if deep_copy else parent_value
    #     else:
    #         return {}

    def __enter__(self):
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(EXECUTION_CONTEXT, self))

        # Enters the context of all jobs
        self.exit_stack.enter_context(stacked_contexts(list(self.jobs.values())))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()


def jobs_to_dict(jobs):
    if jobs is None:
        return {}
    if isinstance(jobs, ExecutionContext):
        return jobs_to_dict([jobs])
    if isinstance(jobs, dict):
        return jobs
    if isinstance(jobs, list):
        return {to_snake_case(job.__class__.__name__): job for job in jobs}


def merge_jobs(*jobs):
    return functools.reduce(lambda x, y: {**x, **y}, map(jobs_to_dict, jobs))


def coalesce(*args):
    """Return the first non-None value from the arguments, or None if all are None."""
    for arg in args:
        if arg is not None:
            return arg
    return None


def execution_context(func):
    @functools.wraps(func)
    async def wrapper(self, **kwargs):
        self.workflow_inputs = kwargs
        with tracer().start_as_current_span(format_span_name(func, self), kind=trace.SpanKind.INTERNAL):
            with self:
                return await func(self, **kwargs)

    return wrapper


EXECUTION_CONTEXT: contextvars.ContextVar[ExecutionContext] = contextvars.ContextVar("execution_context")
