from abc import abstractmethod
from typing import Any

from taskmates.core.execution_context import ExecutionContext, execution_context
from taskmates.core.job import Job
from taskmates.runner.contexts.contexts import Contexts


class TaskmatesWorkflow(ExecutionContext):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, Job] | list[Job] = None,
                 ):
        super().__init__(contexts=contexts, jobs=jobs)
        self.execution_context: ExecutionContext = self

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if 'run' in cls.__dict__:
            cls.run = execution_context(cls.run)

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        pass