import contextlib
import contextvars
import os
from signal import Signals
from typing import Iterator

from .taskmates_extension import TaskmatesExtension
from ..contexts import Contexts
from ..extensions.taskmates_development import TaskmatesDevelopment
from ..extensions.taskmates_dir_loader import TaskmatesDirLoader
from ..extensions.taskmates_working_dir_env import TaskmatesWorkingDirEnv


class ExtensionManager:
    def __init__(self, extensions: list[TaskmatesExtension] = None):
        self.extensions: list[TaskmatesExtension] = extensions or []

    def initialize(self):
        for extension in self.extensions:
            extension.initialize()

    def after_build_contexts(self, contexts: Contexts):
        for extension in self.extensions:
            extension.after_build_contexts(contexts)

    @contextlib.contextmanager
    def completion_context(self, history: str | None,
                           incoming_messages: list[str],
                           contexts: Contexts,
                           signals: Signals,
                           states: dict,
                           ) -> Iterator[tuple[str | None, list[str], Contexts, Signals, dict]]:
        with contextlib.ExitStack() as stack:
            current_history = history
            current_incoming_messages = incoming_messages
            current_contexts = contexts
            current_signals = signals
            current_states = states

            for extension in self.extensions:
                cm = extension.completion_context(
                    current_history,
                    current_incoming_messages,
                    current_contexts,
                    current_signals,
                    current_states
                )
                context_result = stack.enter_context(cm)

                if context_result is not None:
                    (current_history,
                     current_incoming_messages,
                     current_contexts,
                     current_signals,
                     current_states) = context_result

            yield (current_history,
                   current_incoming_messages,
                   current_contexts,
                   current_signals,
                   current_states)

    @contextlib.contextmanager
    def completion_step_context(self, chat, contexts: Contexts, signals: Signals,
                                return_value_processor, interruption_handler, max_steps_manager, states) \
            -> Iterator[tuple[str | None, list[str], Contexts, Signals, dict]]:
        with contextlib.ExitStack() as stack:
            current_chat = chat
            current_contexts = contexts
            current_signals = signals
            current_return_value_processor = return_value_processor
            current_interruption_handler = interruption_handler
            current_max_steps_manager = max_steps_manager
            current_states = states

            for extension in self.extensions:
                cm = extension.completion_step_context(
                    current_chat,
                    current_contexts,
                    current_signals,
                    current_return_value_processor,
                    current_interruption_handler,
                    current_max_steps_manager,
                    current_states
                )
                context_result = stack.enter_context(cm)

                if context_result is not None:
                    (current_chat,
                     current_contexts,
                     current_signals,
                     current_return_value_processor,
                     current_interruption_handler,
                     current_max_steps_manager,
                     current_states) = context_result

            yield (current_chat,
                   current_contexts,
                   current_signals,
                   current_return_value_processor,
                   current_interruption_handler,
                   current_max_steps_manager,
                   current_states)


DEFAULT_EXTENSIONS: list = [TaskmatesDirLoader(),
                            TaskmatesWorkingDirEnv()]

if os.environ.get("TASKMATES_ENV", "production") == "development":
    DEFAULT_EXTENSIONS.append(TaskmatesDevelopment())

EXTENSION_MANAGER: contextvars.ContextVar[ExtensionManager] = \
    contextvars.ContextVar("extension_manager", default=ExtensionManager(DEFAULT_EXTENSIONS))
