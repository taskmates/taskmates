import contextvars
import importlib
import os
import tempfile

import pytest
import sys

from .taskmates_extension import TaskmatesExtension
from ..contexts import Contexts


class ExtensionManager:
    def __init__(self, extensions: list[str] = None):
        additional_extensions = self._get_additional_extensions()
        self.extensions: list[str] = additional_extensions + (extensions or [])
        self._initialized: bool = False
        self._loaded_extensions: list[TaskmatesExtension] = []

    @staticmethod
    def _get_additional_extensions() -> list[str]:
        additional_extensions = os.environ.get('TASKMATES_EXTENSIONS', '')
        return [ext.strip() for ext in additional_extensions.split(',') if ext.strip()]

    def _add_external_directories_to_path(self):
        external_dirs = os.environ.get('TASKMATES_EXTENSIONS_DIRS')
        if external_dirs:
            for directory in external_dirs.split(':'):
                if os.path.isdir(directory) and directory not in sys.path:
                    sys.path.append(directory)

    def _load_extension(self, extension_name: str) -> TaskmatesExtension:
        try:
            module_name, class_name = extension_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            extension_class = getattr(module, class_name)
            extension = extension_class()
            if not isinstance(extension, TaskmatesExtension):
                raise TypeError(f"Extension {extension_name} does not inherit from TaskmatesExtension")
            return extension
        except (ImportError, AttributeError, TypeError) as e:
            raise RuntimeError(f"Failed to load extension {extension_name}: {str(e)}")

    def initialize(self):
        if not self._initialized:
            self._add_external_directories_to_path()
            for extension_name in self.extensions:
                extension = self._load_extension(extension_name)
                if extension:
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

# Last ones are run first
if os.environ.get("TASKMATES_ENV", "production") == "development":
    DEFAULT_EXTENSIONS.append('taskmates.extensions.github_app_token_env_injector.GithubAppTokenEnvInjector')
    DEFAULT_EXTENSIONS.append('taskmates.extensions.dotenv_injector.DotenvInjector')

extension_manager = ExtensionManager(DEFAULT_EXTENSIONS)

EXTENSION_MANAGER: contextvars.ContextVar[ExtensionManager] = contextvars.ContextVar("extension_manager",
                                                                                     default=extension_manager)


def test_add_external_directories_to_path():
    with tempfile.TemporaryDirectory() as temp_dir1, tempfile.TemporaryDirectory() as temp_dir2:
        os.environ['TASKMATES_EXTENSIONS_DIRS'] = f"{temp_dir1}:{temp_dir2}"
        manager = ExtensionManager()
        original_sys_path = sys.path.copy()
        manager._add_external_directories_to_path()
        assert temp_dir1 in sys.path
        assert temp_dir2 in sys.path
        assert sys.path.index(temp_dir1) >= len(original_sys_path)
        assert sys.path.index(temp_dir2) >= len(original_sys_path)
        assert sys.path.index(temp_dir2) > sys.path.index(temp_dir1)
        # Clean up
        sys.path = original_sys_path


def test_load_extension_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['TASKMATES_EXTENSIONS_DIRS'] = temp_dir
        with open(os.path.join(temp_dir, 'mock_extension.py'), 'w') as f:
            f.write("""
from taskmates.sdk.taskmates_extension import TaskmatesExtension

class MockExtension(TaskmatesExtension):
    def initialize(self):
        pass
    def after_build_contexts(self, contexts):
        pass
""")

        sys.path.append(temp_dir)

        manager = ExtensionManager()
        extension = manager._load_extension("mock_extension.MockExtension")

        assert extension is not None
        assert isinstance(extension, TaskmatesExtension)

        sys.path.pop()


def test_load_extension_failure():
    manager = ExtensionManager()
    with pytest.raises(RuntimeError):
        manager._load_extension("non_existent_module.NonExistentExtension")


def test_initialize_with_external_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ['TASKMATES_EXTENSIONS_DIRS'] = temp_dir
        with open(os.path.join(temp_dir, 'test_extension.py'), 'w') as f:
            f.write("""
from taskmates.sdk.taskmates_extension import TaskmatesExtension

class TestExtension(TaskmatesExtension):
    def initialize(self):
        pass
    def after_build_contexts(self, contexts):
        pass
""")

        manager = ExtensionManager(['test_extension.TestExtension'])
        manager.initialize()

        assert len(manager._loaded_extensions) == 1
        assert isinstance(manager._loaded_extensions[0], TaskmatesExtension)


def test_additional_extensions():
    os.environ['TASKMATES_EXTENSIONS'] = 'ext1.Extension1,ext2.Extension2'
    manager = ExtensionManager(['ext3.Extension3'])
    assert manager.extensions == ['ext1.Extension1', 'ext2.Extension2', 'ext3.Extension3']
    del os.environ['TASKMATES_EXTENSIONS']
