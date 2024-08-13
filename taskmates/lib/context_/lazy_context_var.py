from contextvars import ContextVar
from typing import TypeVar, Callable, Union, Generic

from typeguard import typechecked

T = TypeVar('T')


class LazyContextVar(Generic[T]):
    def __init__(self, name: str, default_factory: Callable[[], T]):
        self._var: ContextVar[T] = ContextVar(name)
        self._default_factory: Callable[[], T] = default_factory

    def get(self) -> T:
        try:
            return self._var.get()
        except LookupError:
            default_value = self._default_factory()
            self._var.set(default_value)
            return default_value

    def set(self, value: T) -> None:
        self._var.set(value)


ContextVarLike = Union[ContextVar[T], LazyContextVar[T]]


def increment_context_var(context_var: ContextVarLike[int]) -> None:
    value = context_var.get()
    context_var.set(value + 1)


# Pytest tests


def test_context_var():
    regular_var: ContextVar[int] = ContextVar('regular_var', default=0)
    increment_context_var(regular_var)
    assert regular_var.get() == 1


def test_lazy_context_var():
    lazy_var: LazyContextVar[int] = LazyContextVar('lazy_var', lambda: 0)
    increment_context_var(lazy_var)
    assert lazy_var.get() == 1


def test_lazy_context_var_default_factory():
    call_count = 0

    def default_factory():
        nonlocal call_count
        call_count += 1
        return 10

    lazy_var: LazyContextVar[int] = LazyContextVar('lazy_var', default_factory)
    assert lazy_var.get() == 10
    assert call_count == 1
    assert lazy_var.get() == 10
    assert call_count == 1  # default_factory should only be called once


def test_context_var_like_type_checking():
    @typechecked
    def takes_context_var_like(var: ContextVarLike[int]):
        increment_context_var(var)

    regular_var: ContextVar[int] = ContextVar('regular_var', default=0)
    lazy_var: LazyContextVar[int] = LazyContextVar('lazy_var', lambda: 0)

    takes_context_var_like(regular_var)
    takes_context_var_like(lazy_var)
