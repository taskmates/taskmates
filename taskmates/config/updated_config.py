import contextvars
from contextlib import contextmanager
from typing import TypeVar

T = TypeVar('T')


@contextmanager
def updated_config(var: contextvars.ContextVar[T], value: T):
    current_value = var.get()
    merged_value = {**current_value, **value}
    token = var.set(merged_value)
    try:
        yield merged_value
    finally:
        var.reset(token)
