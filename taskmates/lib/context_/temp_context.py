import contextlib
import contextvars
from typing import TypeVar, Iterator

T = TypeVar('T')


@contextlib.contextmanager
def temp_context(var: contextvars.ContextVar[T], value: T) -> contextlib.AbstractContextManager[T]:
    # Save the current state of the ContextVar
    token = var.set(value)
    try:
        yield value
    finally:
        # Reset the ContextVar to its previous state
        var.reset(token)


# # Usage example
#
# # Create a ContextVar
# my_var = contextvars.ContextVar('my_var')
#
# my_var.set(42)
# print(my_var.get())  # Output: 42
#
# with temp_context(my_var, 100):
#     print(my_var.get())  # Output: 100
#
# print(my_var.get())  # Output: 42 (reset to the original value)
