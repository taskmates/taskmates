import contextlib
import contextvars
import copy
import functools
from contextlib import AbstractContextManager
from typing import TypedDict

from blinker import Namespace, Signal
from loguru import logger
from opentelemetry import trace
from ordered_set import OrderedSet

from taskmates.core.job import Job
from taskmates.core.signals.artifact_signals import ArtifactSignals
from taskmates.core.signals.control_signals import ControlSignals
from taskmates.core.signals.inputs_signals import InputsSignals
from taskmates.core.signals.outputs_signals import OutputsSignals
from taskmates.core.signals.status_signals import StatusSignals
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.runner.contexts.contexts import Contexts
from taskmates.taskmates_runtime import TASKMATES_RUNTIME

Signal.set_class = OrderedSet


class InterruptRequestMediator(Job):
    def __init__(self):
        self.interrupt_requested = False

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().control.interrupt.send_async({})
            self.interrupt_requested = True

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.control.interrupt_request.connect(self.handle_interrupt_request, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.control.interrupt_request.disconnect(self.handle_interrupt_request)


class ReturnValueCollector(Job):
    def __init__(self):
        self.return_value = NOT_SET

    def get(self):
        return self.return_value

    async def handle_return_value(self, status):
        self.return_value = status

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.result.connect(self.handle_return_value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.outputs.result.disconnect(self.handle_return_value)

    def get_result(self):
        return self.return_value


class InterruptedOrKilled(Job):
    def __init__(self):
        self.interrupted_or_killed = False

    def get(self):
        return self.interrupted_or_killed

    async def handle_interrupted(self, _sender):
        self.interrupted_or_killed = True

    async def handle_killed(self, _sender):
        self.interrupted_or_killed = True

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get()
        signals.status.interrupted.connect(self.handle_interrupted, weak=False)
        signals.status.killed.connect(self.handle_killed, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get()
        signals.status.interrupted.disconnect(self.handle_interrupted)
        signals.status.killed.disconnect(self.handle_killed)


class ExecutionContextState(TypedDict):
    interrupted_or_killed: InterruptedOrKilled
    return_value: ReturnValueCollector


def coalesce(*args):
    """Return the first non-None value from the arguments, or None if all are None."""
    for arg in args:
        if arg is not None:
            return arg
    return None


class ExecutionContext(AbstractContextManager):
    def __init__(self,
                 # TODO: name
                 # name: str = None,
                 contexts: Contexts = None,
                 jobs: dict[str, Job] | list[Job] = None,
                 ):
        self.namespace = Namespace()
        self.parent: ExecutionContext = EXECUTION_CONTEXT.get(None)

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

        self.workflow_inputs = {}

        self.parent_jobs = getattr(self.parent, 'parent_jobs', {})
        if not self.parent:
            self.parent_jobs["root"] = self
        else:
            self.parent_jobs[to_snake_case(self.__class__.__name__)] = self

        if isinstance(jobs, list):
            jobs = {to_snake_case(job.__class__.__name__): job for job in jobs}

        if not self.parent and not jobs:
            jobs = {
                # TODO: job state
                "interrupt_request_mediator": InterruptRequestMediator(),
                "interrupted_or_killed": InterruptedOrKilled(),
                # TODO: job output
                "return_value": ReturnValueCollector(),
            }

        if jobs is None:
            jobs = {}

        self.jobs = jobs

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
        self.token = EXECUTION_CONTEXT.set(self)
        self.exit_stack = contextlib.ExitStack()
        self.exit_stack.enter_context(temp_context(EXECUTION_CONTEXT, self))
        self.exit_stack.enter_context(stacked_contexts(list(self.jobs.values())))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()
        EXECUTION_CONTEXT.reset(self.token)


def execution_context(func):
    @functools.wraps(func)
    async def wrapper(self, **kwargs):
        self.workflow_inputs = kwargs
        with tracer().start_as_current_span(format_span_name(func, self), kind=trace.SpanKind.INTERNAL):
            with self:
                return await func(self, **kwargs)

    return wrapper


EXECUTION_CONTEXT: contextvars.ContextVar[ExecutionContext] = contextvars.ContextVar("execution_context")
