import functools
from abc import abstractmethod
from typing import Any

from taskmates.core.execution_context import execution_context, ExecutionContext
from taskmates.runner.contexts.contexts import Contexts


class TaskmatesWorkflow(ExecutionContext):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, ExecutionContext] | list[ExecutionContext] = None,
                 inputs: dict = None,
                 ):
        super().__init__(contexts=contexts, jobs=jobs, inputs=inputs)
        self.execution_context: ExecutionContext = self

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'run' in cls.__dict__:
            cls.run = execution_context(cls.run)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass
