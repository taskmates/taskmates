import contextvars
import importlib
import os

from .taskmates_extension import TaskmatesExtension
from ..contexts import Contexts


class ExtensionManager:
    def __init__(self, extensions: list[str] = None):
        self.extensions: list[str] = extensions or []
        self._initialized: bool = False
        self._loaded_extensions: list[TaskmatesExtension] = []

    def _load_extension(self, extension_name: str) -> TaskmatesExtension:
        module_name, class_name = extension_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        extension_class = getattr(module, class_name)
        return extension_class()

    def initialize(self):
        if not self._initialized:
            for extension_name in self.extensions:
                extension = self._load_extension(extension_name)
                extension.initialize()
                self._loaded_extensions.append(extension)
            self._initialized = True

    def after_build_contexts(self, contexts: Contexts):
        for extension in self._loaded_extensions:
            extension.after_build_contexts(contexts)


DEFAULT_EXTENSIONS: list[str] = [
    'taskmates.extensions.taskmates_dirs_loader.TaskmatesDirsLoader',
    'taskmates.extensions.taskmates_working_dir_env.TaskmatesWorkingDirEnv'
]

if os.environ.get("TASKMATES_ENV", "production") == "development":
    DEFAULT_EXTENSIONS.append('taskmates.extensions.taskmates_development.TaskmatesDevelopment')

extension_manager = ExtensionManager(DEFAULT_EXTENSIONS)

EXTENSION_MANAGER: contextvars.ContextVar[ExtensionManager] = contextvars.ContextVar("extension_manager",
                                                                                     default=extension_manager)
