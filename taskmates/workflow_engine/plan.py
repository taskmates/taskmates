from abc import abstractmethod
from typing import Any

from taskmates.workflow_engine.daemon import Daemon
from taskmates.workflow_engine.run import RUN
from taskmates.workflows.contexts.context import Context


class Plan:
    async def create_context(self, **kwargs) -> Context:
        return RUN.get().context.copy()

    async def create_signals(self) -> dict[str, Any]:
        return {}

    async def create_daemons(self) -> dict[str, Daemon]:
        return {}

    async def create_state(self) -> dict[str, Any]:
        pass

    @abstractmethod
    async def steps(self, *args, **kwargs) -> Any:
        pass
