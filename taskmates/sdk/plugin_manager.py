import importlib

from pkg_resources import iter_entry_points

from .taskmates_plugin import TaskmatesPlugin


class PluginManager:
    def __init__(self):
        self.plugins = []

    def load_plugins(self):
        for entry_point in iter_entry_points(group='taskmates.plugins'):
            plugin_class = entry_point.load()
            if issubclass(plugin_class, TaskmatesPlugin):
                plugin = plugin_class()
                if self._check_plugin_dependencies(plugin):
                    self.plugins.append(plugin)
                else:
                    print(f"Skipping plugin {plugin.name} due to missing dependencies")

    def initialize_plugins(self):
        for plugin in self.plugins:
            plugin.initialize()

    def _check_plugin_dependencies(self, plugin: TaskmatesPlugin) -> bool:
        for dependency in plugin.required_dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                print(f"Warning: Plugin {plugin.name} is missing required dependency: {dependency}")
                return False
        return True

#
# def load_plugin_from_path(path):
#     spec = importlib.util.spec_from_file_location("plugin", path)
#     module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(module)
#     for item_name in dir(module):
#         item = getattr(module, item_name)
#         if isinstance(item, type) and issubclass(item, PluginInterface) and item is not PluginInterface:
#             return item()
#     return None
#
# async def load_plugins(plugin_dirs):
#     plugins = []
#     for plugin_dir in plugin_dirs:
#         for filename in os.listdir(plugin_dir):
#             if filename.endswith(".py"):
#                 plugin = load_plugin_from_path(os.path.join(plugin_dir, filename))
#                 if plugin:
#                     await plugin.initialize(app)
#                     await plugin.register_routes(app)
#                     plugins.append(plugin)
#     return plugins
#
#
#
# plugin_dirs = [
#     "./plugins",  # Local development plugins
#     "/path/to/other/plugin/directory"
# ]
# await load_plugins(plugin_dirs)

# ```python
# import os
#
# plugin_dirs = [
#     "./plugins",
#     *os.environ.get("EXTRA_PLUGIN_DIRS", "").split(os.pathsep)
# ]
# ```
#
# Developers can then run the server with:
#
# ```bash
# EXTRA_PLUGIN_DIRS="/path/to/my/plugin" python dev_server.py
# ```
