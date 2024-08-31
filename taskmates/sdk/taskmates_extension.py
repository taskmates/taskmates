from abc import ABC


class TaskmatesExtension(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def initialize(self):
        """Initialize the extension."""
        pass
