from abc import abstractmethod
from contextlib import AbstractContextManager
from typing import Any, Optional

from taskmates.workflows.contexts.run_context import RunContext


class Plan:
    @abstractmethod
    async def steps(self, *args, **kwargs) -> Any:
        pass
