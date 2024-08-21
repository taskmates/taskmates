import contextvars
import os
import aspectlib

from .taskmates_extension import TaskmatesExtension
from ..contexts import Contexts
from ..extensions.taskmates_development import TaskmatesDevelopment
from ..extensions.taskmates_dirs_loader import TaskmatesDirsLoader
from ..extensions.taskmates_working_dir_env import TaskmatesWorkingDirEnv


class ExtensionManager:
    def __init__(self, extensions: list[TaskmatesExtension] = None):
        self.extensions: list[TaskmatesExtension] = extensions or []

    def initialize(self, target_class):
        for extension in self.extensions:
            extension.initialize()
            aspectlib.weave(target_class, extension.completion_context)
            aspectlib.weave(target_class, extension.completion_step_context)

    def after_build_contexts(self, contexts: Contexts):
        for extension in self.extensions:
            extension.after_build_contexts(contexts)


DEFAULT_EXTENSIONS: list = [TaskmatesDirsLoader(),
                            TaskmatesWorkingDirEnv()]

if os.environ.get("TASKMATES_ENV", "production") == "development":
    DEFAULT_EXTENSIONS.append(TaskmatesDevelopment())

EXTENSION_MANAGER: contextvars.ContextVar[ExtensionManager] = \
    contextvars.ContextVar("extension_manager", default=ExtensionManager(DEFAULT_EXTENSIONS))
