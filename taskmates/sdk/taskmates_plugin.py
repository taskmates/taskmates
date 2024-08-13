from abc import ABC, abstractmethod


class TaskmatesPlugin(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize the plugin."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version of the plugin."""
        pass

    @property
    def required_dependencies(self) -> list[str]:
        """Return a list of required dependencies."""
        return []

# To register
#
# ```python
# # setup.py
# from setuptools import setup
#
# setup(
#     name='my-plugin',
#     # ... other setup parameters ...
#     entry_points={
#         'your_project.plugins': [
#             'my_plugin = my_plugin.main:MyPlugin',
#         ],
#     },
# )
# ```
