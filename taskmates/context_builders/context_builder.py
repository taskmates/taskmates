from abc import ABC, abstractmethod

from taskmates.runner.contexts.contexts import Contexts


class ContextBuilder(ABC):
    @abstractmethod
    def build(self) -> Contexts:
        pass


def test_context_builder():
    # We can't directly test an abstract class, but we can ensure it's defined correctly
    assert hasattr(ContextBuilder, 'build')
    assert callable(getattr(ContextBuilder, 'build'))
