import functools
from abc import ABC
from abc import abstractmethod
from typing import Any

from opentelemetry import trace

from taskmates.core.execution_context import ExecutionContext
from taskmates.core.processor import Processor
from taskmates.lib.opentelemetry_.format_span_name import format_span_name
from taskmates.lib.opentelemetry_.tracing import tracer
from taskmates.runner.contexts.contexts import Contexts


class TaskmatesWorkflow(ABC):
    def __init__(self, *,
                 contexts: Contexts,
                 processors: list[Processor] = None
                 ):
        self.execution_context = ExecutionContext(contexts=contexts, processors=processors)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'run' in cls.__dict__:
            cls.run = cls.run_decorator(cls.run)

    @classmethod
    def run_decorator(cls, func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            with tracer().start_as_current_span(format_span_name(func, self), kind=trace.SpanKind.INTERNAL), \
                    self.execution_context.context():
                return await func(self, *args, **kwargs)

        return wrapper

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass
