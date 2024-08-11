import contextvars
import copy
from contextlib import contextmanager
from typing import TypeVar

from typeguard import typechecked

T = TypeVar('T')


@contextmanager
@typechecked
def context_fork(context: contextvars.ContextVar[T]):
    clone = copy.deepcopy(context.get())
    token = context.set(clone)
    try:
        yield clone
    finally:
        context.reset(token)
