from abc import ABC
from typing import Any


class TaskmatesWorkflow(ABC):
    async def run(self, *args, **kwargs) -> Any:
        pass
