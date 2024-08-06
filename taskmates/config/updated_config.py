import contextvars
from contextlib import contextmanager
from typing import TypeVar

T = TypeVar('T')


@contextmanager
def updated_config(config: contextvars.ContextVar[T], value: T):
    merged_value, token = update_config(config, value)
    try:
        yield merged_value
    finally:
        config.reset(token)


def update_config(config, value):
    merged_value = merge_config(config, value)
    token = config.set(merged_value)
    return merged_value, token


def merge_config(config, value):
    current_value = config.get()
    merged_value = {**current_value, **value}
    return merged_value
