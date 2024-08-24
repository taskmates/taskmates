from abc import ABC

from taskmates.contexts import Contexts


class TaskmatesExtension(ABC):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def initialize(self):
        """Initialize the extension."""
        pass

    def after_build_contexts(self, contexts: Contexts):
        pass
