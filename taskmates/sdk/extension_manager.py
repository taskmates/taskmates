import contextvars
import os

from .taskmates_extension import TaskmatesExtension
from ..contexts import Contexts
from ..extensions.taskmates_development import TaskmatesDevelopment
from ..extensions.taskmates_dirs_loader import TaskmatesDirsLoader
from ..extensions.taskmates_working_dir_env import TaskmatesWorkingDirEnv


class ExtensionManager:
    def __init__(self, extensions: list[TaskmatesExtension] = None):
        self.extensions: list[TaskmatesExtension] = extensions or []
        self._initialized: bool = False

    def initialize(self):
        if not self._initialized:
            for extension in self.extensions:
                extension.initialize()
            self._initialized = True

    def after_build_contexts(self, contexts: Contexts):
        for extension in self.extensions:
            extension.after_build_contexts(contexts)


DEFAULT_EXTENSIONS: list = [TaskmatesDirsLoader(),
                            TaskmatesWorkingDirEnv()]

if os.environ.get("TASKMATES_ENV", "production") == "development":
    DEFAULT_EXTENSIONS.append(TaskmatesDevelopment())

extension_manager = ExtensionManager(DEFAULT_EXTENSIONS)
extension_manager.initialize()

EXTENSION_MANAGER: contextvars.ContextVar[ExtensionManager] = contextvars.ContextVar("extension_manager",
                                                                                     default=extension_manager)
