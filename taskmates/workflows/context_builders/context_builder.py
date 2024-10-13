from abc import ABC, abstractmethod

from taskmates.workflows.contexts.context import Context


class ContextBuilder(ABC):
    @abstractmethod
    def build(self) -> Context:
        pass


def test_context_builder():
    # We can't directly test an abstract class, but we can ensure it's defined correctly
    assert hasattr(ContextBuilder, 'build')
    assert callable(getattr(ContextBuilder, 'build'))
