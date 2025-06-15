from abc import abstractmethod
from typing import Any


class Plan:
    @abstractmethod
    async def steps(self, *args, **kwargs) -> Any:
        pass
