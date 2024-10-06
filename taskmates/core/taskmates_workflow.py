import functools
from abc import abstractmethod
from typing import Any

from opentelemetry import trace

from taskmates.core.run import Run
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.lib.str_.to_snake_case import to_snake_case
from taskmates.runner.contexts.contexts import Contexts


class TaskmatesWorkflow:
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, Run] | list[Run] = None,
                 ):
        self._contexts = contexts
        self._jobs = jobs

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'run' in cls.__dict__:
            cls.run = run(cls.run)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass


def run(func):
    """
    Decorator to wrap a function with a Run
    :param func: function to wrap
    :return: wrapped function
    """

    @functools.wraps(func)
    async def wrapper(self, **kwargs):
        name = to_snake_case(self.__class__.__name__)
        run_context = Run(name=name,
                          callable=func,
                          inputs={"self": self, **kwargs},
                          contexts=self._contexts,
                          jobs=self._jobs)
        with tracer().start_as_current_span(format_span_name(func, self), kind=trace.SpanKind.INTERNAL):
            run_context.start()
            if kwargs.get('return_run', False):
                return run_context
            return await run_context.get_result()

    return wrapper
