from abc import ABC

import aspectlib

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

    @aspectlib.Aspect
    def completion_context(self, *args, **kwargs):
        result = yield aspectlib.Proceed
        return result

    @aspectlib.Aspect
    def completion_step_context(self, *args, **kwargs):
        result = yield aspectlib.Proceed
        return result
