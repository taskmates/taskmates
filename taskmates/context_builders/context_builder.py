from abc import ABC, abstractmethod

from taskmates.runner.contexts.runner_context import RunnerContext


class ContextBuilder(ABC):
    @abstractmethod
    def build(self) -> RunnerContext:
        pass


def test_context_builder():
    # We can't directly test an abstract class, but we can ensure it's defined correctly
    assert hasattr(ContextBuilder, 'build')
    assert callable(getattr(ContextBuilder, 'build'))
