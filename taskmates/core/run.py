import asyncio
import contextlib
import contextvars
import copy
from contextlib import AbstractContextManager
from typing import Callable

from blinker import Namespace, Signal
from ordered_set import OrderedSet

from taskmates.core.coalesce import coalesce
from taskmates.core.signals.control_signals import ControlSignals
from taskmates.core.signals.input_streams import InputStreams
from taskmates.core.signals.output_streams import OutputStreams
from taskmates.core.signals.status_signals import StatusSignals
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.runner.contexts.runner_context import RunnerContext
from taskmates.taskmates_runtime import TASKMATES_RUNTIME

Signal.set_class = OrderedSet


class Run(AbstractContextManager):
    def __init__(self,
                 name: str = None,
                 callable: Callable = None,
                 contexts: RunnerContext = None,
                 inputs: dict = None,
                 jobs: dict[str, 'Run'] | list['Run'] = None,
                 ):
        self.namespace = Namespace()
        self.parent: Run = RUN.get(None)
        self.name = name or "root"
        self.callable = callable

        self.run_task = None

        self.exit_stack = contextlib.ExitStack()

        self.contexts: RunnerContext = copy.deepcopy(coalesce(contexts, getattr(self.parent, 'contexts', {})))
        self.inputs = inputs or {}

        self.control = getattr(self.parent, 'control', ControlSignals())
        self.status = getattr(self.parent, 'status', StatusSignals())
        self.input_streams = getattr(self.parent, 'input_streams', InputStreams())
        self.output_streams = getattr(self.parent, 'output_streams', OutputStreams())

        self.outputs: dict = {}

        self.jobs = jobs_to_dict(jobs)
        self.jobs_registry = getattr(self.parent, 'jobs_registry', {})

        # Check and add each job from self.jobs
        for job_name, job in self.jobs.items():
            self.jobs_registry[job_name] = job
            # TODO: reenable
            # self._check_and_add_job(job_name, job)

    def _check_and_add_job(self, job_name: str, job: 'Run'):
        if job_name in self.jobs_registry:
            raise ValueError(f"Job '{job_name}' is already in the registry. Duplicate job names are not allowed.")
        self.jobs_registry[job_name] = job

    # def assign_context(self, value, parent_value, deep_copy=False):
    #     if value is not None:
    #         return value
    #     elif parent_value is not None:
    #         return copy.deepcopy(parent_value) if deep_copy else parent_value
    #     else:
    #         return {}

    def start(self):
        self.run_task = asyncio.create_task(self._run())

    async def _run(self):
        with self:
            return await self.callable(**self.inputs)

    async def get_result(self):
        return await self.run_task

    def __enter__(self):
        TASKMATES_RUNTIME.get().initialize()

        # Sets the current execution context
        self.exit_stack.enter_context(temp_context(RUN, self))

        # Enters the context of all jobs
        self.exit_stack.enter_context(stacked_contexts(list(self.jobs.values())))

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name})"


RUN: contextvars.ContextVar[Run] = contextvars.ContextVar("run")


def jobs_to_dict(jobs):
    if jobs is None:
        return {}
    if isinstance(jobs, Run):
        return jobs_to_dict([jobs])
    if isinstance(jobs, dict):
        return jobs
    if isinstance(jobs, list):
        return {to_snake_case(job.__class__.__name__): job for job in jobs}
