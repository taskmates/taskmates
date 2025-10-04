import contextlib
from contextlib import AbstractContextManager


class CompositeContextManager(AbstractContextManager):
    def __init__(self):
        self.exit_stack = contextlib.ExitStack()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()

    def __repr__(self):
        return f"{self.__class__.__name__}()"

