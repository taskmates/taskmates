import contextlib
from abc import ABC
from signal import Signals
from typing import Iterator

from taskmates.contexts import Contexts

enabled_extensions = []


class TaskmatesExtension(ABC):
    def initialize(self):
        """Initialize the extension."""
        pass

    @property
    def name(self) -> str:
        """Return the name of the extension."""
        return self.__class__.__name__

    def after_build_contexts(self, contexts: Contexts):
        pass

    @contextlib.contextmanager
    def completion_context(self, history: str | None,
                           incoming_messages: list[str],
                           contexts: Contexts,
                           signals: Signals,
                           states: dict,
                           ) -> Iterator[tuple[str | None, list[str], Contexts, Signals, dict]]:
        yield history, incoming_messages, contexts, signals, states

    @contextlib.contextmanager
    def completion_step_context(self, chat, contexts: Contexts, signals: Signals,
                                return_value_processor, interruption_handler, max_steps_manager, states) \
            -> Iterator[tuple[str | None, list[str], Contexts, Signals, dict]]:
        yield chat, contexts, signals, return_value_processor, interruption_handler, max_steps_manager, states
