import importlib
import importlib.util
import sys
import os
from contextlib import contextmanager
from typing import Dict, Type, Callable, List

# Registry to hold superclasses and their list of callbacks
if 'subclass_registry' not in globals():
    subclass_registry: Dict[Type, List[Callable[[Type], None]]] = {}


class SubclassDetectingMeta(type):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        # Check if any base class is in the constructors
        for base in cls.__bases__:
            if base in subclass_registry:
                # Call the registered callbacks for this superclass
                for callback in subclass_registry[base]:
                    callback(cls)


# This context manager will help us to avoid recursion
@contextmanager
def _prevent_recursion():
    if hasattr(_prevent_recursion, 'handling'):
        yield True
    else:
        _prevent_recursion.handling = True
        try:
            yield False
        finally:
            delattr(_prevent_recursion, 'handling')


class CustomFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        # Check if we're already handling an import to prevent recursion
        with _prevent_recursion() as is_handling:
            if is_handling:
                # We're already handling an import, so return None
                return None

            spec = importlib.util.find_spec(fullname)
            if spec and spec.loader:
                original_loader = spec.loader
                spec.loader = CustomLoader(original_loader)
            return spec


class CustomLoader(importlib.abc.Loader):
    def __init__(self, original_loader):
        self.original_loader = original_loader

    def create_module(self, spec):
        return self.original_loader.create_module(spec)

    def exec_module(self, module):
        self.original_loader.exec_module(module)
        for name, value in vars(module).items():
            if isinstance(value, type):
                for base in value.__bases__:
                    if base in subclass_registry:
                        # Modify the class to use the metaclass
                        value.__class__ = SubclassDetectingMeta
                        # Call the registered callbacks for this superclass
                        for callback in subclass_registry[base]:
                            callback(value)


def register_superclass_callback(superclass: Type, callback: Callable[[Type], None]):
    """Register a callback to be called when a subclass of the given superclass is imported."""
    if superclass not in subclass_registry:
        subclass_registry[superclass] = []
    subclass_registry[superclass].append(callback)


# Register the custom finder
if os.environ.get('TASKMATES_TELEMETRY_ENABLED', '0') == '1':
    if not any(isinstance(finder, CustomFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, CustomFinder())

# # Example usage:
# # Assuming SuperClass is defined in a third-party library
# class SuperClass:
#     pass
#
#
# # Define a callback function
# def my_callback(subclass):
#     print(f"New subclass detected: {subclass.__name__}")
#
# # Define another callback function
# def my_other_callback(subclass):
#     print(f"Another subclass detected: {subclass.__name__}")
#
#
# # Register the superclass and callbacks
# register_superclass_callback(SuperClass, my_callback)
# register_superclass_callback(SuperClass, my_other_callback)
#
# # Now, any imports that happen after this registration could be intercepted
# # and modified by the CustomFinder and CustomLoader
