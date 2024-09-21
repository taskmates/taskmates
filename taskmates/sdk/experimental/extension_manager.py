import contextvars
import importlib
import os
import tempfile

import pytest
import sys

from taskmates.sdk.experimental.taskmates_extension import TaskmatesExtension


class ExtensionManager:
    def __init__(self, extensions: list[str] = None):
        self.extensions: list[str] = extensions or []
        self._initialized: bool = False
        self._loaded_extensions: list[TaskmatesExtension] = []

    @staticmethod
    def _get_additional_extensions() -> list[str]:
        if os.environ.get("TASKMATES_ENV", "production") == "development":
            DEFAULT_EXTENSIONS.append('taskmates.extensions.github_app_token_env_injector.GithubAppTokenEnvInjector')
            DEFAULT_EXTENSIONS.append('taskmates.extensions.dotenv_injector.DotenvInjector')

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
            additional_extensions = self._get_additional_extensions()
            for extension_name in self.extensions + additional_extensions:
                extension = self._load_extension(extension_name)
                if extension:
                    extension.initialize()
                    self._loaded_extensions.append(extension)
            self._initialized = True

    def shutdown(self):
        for extension in self._loaded_extensions:
            extension.shutdown()


# Last ones are run first
DEFAULT_EXTENSIONS: list[str] = [
    'taskmates.extensions.taskmates_dirs_loader.TaskmatesDirsLoader',
    'taskmates.extensions.taskmates_working_dir_env.TaskmatesWorkingDirEnv',
]

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
from taskmates.sdk.experimental.taskmates_extension import TaskmatesExtension

class MockExtension(TaskmatesExtension):
    def initialize(self):
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


# TODO: rewrite these tests to NOT call .initialize
#
# def test_initialize_with_external_directory():
#     assert os.environ['TASKMATES_ENV'] == 'test'
#
#     with tempfile.TemporaryDirectory() as temp_dir:
#         os.environ['TASKMATES_EXTENSIONS_DIRS'] = temp_dir
#         with open(os.path.join(temp_dir, 'test_extension.py'), 'w') as f:
#             f.write("""
# from taskmates.sdk.experimental.taskmates_extension import TaskmatesExtension
#
# class TestExtension(TaskmatesExtension):
#     def initialize(self):
#         pass
#     def after_build_contexts(self, contexts):
#         pass
# """)
#
#         manager = ExtensionManager(['test_extension.TestExtension'])
#         manager.initialize()
#
#         assert manager._loaded_extensions == [TaskmatesExtension]
#
#     # Clean up
#     del os.environ['TASKMATES_EXTENSIONS_DIRS']
#     del os.environ['TASKMATES_ENV']
#
#
# def test_additional_extensions():
#     assert os.environ['TASKMATES_ENV'] == 'test'  # Ensure we're not in development mode
#
#     os.environ[
#         'TASKMATES_EXTENSIONS'] = 'taskmates.extensions.taskmates_dirs_loader.TaskmatesDirsLoader,taskmates.extensions.taskmates_working_dir_env.TaskmatesWorkingDirEnv'
#     manager = ExtensionManager(['taskmates.extensions.taskmates_dirs_loader.TaskmatesDirsLoader'])
#     manager.initialize()
#     expected_extensions = ['taskmates.extensions.taskmates_dirs_loader.TaskmatesDirsLoader',
#                            'taskmates.extensions.taskmates_working_dir_env.TaskmatesWorkingDirEnv']
#     assert all(ext in manager.extensions + manager._get_additional_extensions() for ext in expected_extensions)
#     assert len(manager.extensions + manager._get_additional_extensions()) == len(expected_extensions)
#     del os.environ['TASKMATES_EXTENSIONS']
