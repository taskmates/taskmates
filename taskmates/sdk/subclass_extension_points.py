import importlib
import importlib.util
from abc import ABCMeta
from contextlib import contextmanager
from importlib.machinery import ExtensionFileLoader
from typing import Dict, Type, Callable, List, Tuple, TypedDict, is_typeddict, Set

import pytest
import sys
from pydantic_core import SchemaValidator
from wrapt import ObjectProxy

# Registry to hold superclasses and their list of callbacks
subclass_registry: Dict[Tuple[str, str], List[Callable[[Type], None]]] = {}

# Whitelist for classes that should be instrumented
class_whitelist: Set[Type] = set()


class SubclassExtensionPoints(importlib.abc.MetaPathFinder):
    @staticmethod
    def initialize():
        if not any(isinstance(finder, SubclassExtensionPoints) for finder in sys.meta_path):
            sys.meta_path.insert(0, SubclassExtensionPoints())

    def find_spec(self, fullname, path, target=None):
        with _prevent_recursion() as is_handling:
            if is_handling:
                return None
            spec = importlib.util.find_spec(fullname)
            # Only apply if ExtensionFileLoader
            if spec and isinstance(spec.loader, ExtensionFileLoader):
                original_loader = spec.loader
                spec.loader = SubclassDetectingMetaclassLoader(original_loader)
            return spec


def add_to_whitelist(cls: Type):
    """Add a class to the whitelist for instrumentation."""
    class_whitelist.add(cls)


class SubclassDetectingMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace):
        try:
            cls = super().__new__(mcs, name, bases, namespace)
        except Exception as error:
            raise error
        for base in bases:
            key = (base.__module__, base.__name__)
            if key in subclass_registry:
                for callback in subclass_registry[key]:
                    callback(cls)
        return cls


def should_instrument_module(module):
    if not isinstance(module, type):
        return False

    original_metaclass = type(module)

    if issubclass(original_metaclass, SubclassDetectingMeta):
        return False

    # Check if the class is in the whitelist
    if module in class_whitelist:
        return True

    if "taskmates" not in module.__module__:
        return False

    # Allow classes defined in taskmates modules
    return (isinstance(module, type) and
            type(module).__name__ in ('ABCMeta', 'type')
            )


def apply_subclass_detecting_metaclass(cls: Type) -> Type:
    """Apply SubclassDetectingMeta to a class while preserving its original metaclass."""
    if not should_instrument_module(cls):
        return cls

    return SubclassDetectingMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))


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


class SubclassDetectingMetaclassLoader(importlib.abc.Loader):
    def __init__(self, original_loader):
        self.original_loader = original_loader

    def create_module(self, spec):
        return self.original_loader.create_module(spec)

    def exec_module(self, module):
        self.original_loader.exec_module(module)
        for name, value in list(vars(module).items()):
            if should_instrument_module(value):
                setattr(module, name, apply_subclass_detecting_metaclass(value))


def register_superclass_callback(superclass: Type, callback: Callable[[Type], None]):
    """Register a callback to be called when a subclass of the given superclass is imported."""
    if not should_instrument_module(superclass):
        raise TypeError(f"Cannot register callbacks for {superclass.__name__} classes")

    key = (superclass.__module__, superclass.__name__)
    if key not in subclass_registry:
        subclass_registry[key] = []
    subclass_registry[key].append(callback)
    return apply_subclass_detecting_metaclass(superclass)


# Tests

def test_register_superclass_callback():
    class TestSuperClass:
        pass

    # Add TestSuperClass to the whitelist
    add_to_whitelist(TestSuperClass)

    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    TestSuperClass = register_superclass_callback(TestSuperClass, callback)

    # Check if the superclass is in the registry
    key = (TestSuperClass.__module__, TestSuperClass.__name__)
    assert key in subclass_registry
    assert callback in subclass_registry[key]

    # Create a subclass to trigger the callback
    class TestSubClass(TestSuperClass):
        pass

    assert callback_called, "Callback was not called when subclass was created"


def test_sublcass_import_hook(tmp_path):
    # Create temporary files for superclass and subclass
    superclass_content = """
class TestSuperClass:
    pass
"""
    subclass_content = """
from superclass_module import TestSuperClass

class TestSubClass(TestSuperClass):
    pass
"""
    superclass_file = tmp_path / "superclass_module.py"
    subclass_file = tmp_path / "subclass_module.py"
    superclass_file.write_text(superclass_content)
    subclass_file.write_text(subclass_content)

    # Add tmp_path to sys.path and set up CustomFinder
    sys.path.insert(0, str(tmp_path))

    SubclassExtensionPoints().initialize()

    try:
        # Import the superclass module
        superclass_module = importlib.import_module("superclass_module")

        # Add TestSuperClass to the whitelist
        add_to_whitelist(superclass_module.TestSuperClass)

        # Register a callback for TestSuperClass
        callback_called = False

        def callback(cls):
            nonlocal callback_called
            callback_called = True

        superclass_module.TestSuperClass = register_superclass_callback(superclass_module.TestSuperClass, callback)

        # Import the subclass module
        subclass_module = importlib.import_module("subclass_module")

        # Check if TestSubClass uses SubclassDetectingMeta
        assert isinstance(subclass_module.TestSubClass,
                          SubclassDetectingMeta), "TestSubClass should use SubclassDetectingMeta"
        assert callback_called, "Callback should have been called when TestSubClass was created"

    finally:
        # Clean up
        sys.path.pop(0)
        sys.meta_path.pop(0)


def test_typed_dict_handling():
    class MyTypedDict(TypedDict):
        name: str
        age: int

    # Attempt to register a callback for MyTypedDict
    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    with pytest.raises(TypeError, match="Cannot register callbacks for MyTypedDict classes"):
        register_superclass_callback(MyTypedDict, callback)

    # Check that MyTypedDict is not modified
    assert is_typeddict(MyTypedDict), "MyTypedDict should remain a TypedDict"
    assert not isinstance(MyTypedDict, SubclassDetectingMeta), "MyTypedDict should not use SubclassDetectingMeta"

    # Create a subclass of MyTypedDict
    class ExtendedTypedDict(MyTypedDict):
        extra: bool

    # Check that ExtendedTypedDict is also not modified
    assert is_typeddict(ExtendedTypedDict), "ExtendedTypedDict should remain a TypedDict"
    assert not isinstance(ExtendedTypedDict,
                          SubclassDetectingMeta), "ExtendedTypedDict should not use SubclassDetectingMeta"

    # Check that the callback was not called
    assert not callback_called, "Callback should not have been called for TypedDict subclassing"


def test_registry_entries_on_import(tmp_path):
    # Create temporary files for superclass and subclass
    superclass_content = """
class TestSuperClassForRegistry:
    pass
"""
    subclass_content = """
from superclass_registry_module import TestSuperClassForRegistry

class TestSubClassForRegistry(TestSuperClassForRegistry):
    pass
"""
    superclass_file = tmp_path / "superclass_registry_module.py"
    subclass_file = tmp_path / "subclass_registry_module.py"
    superclass_file.write_text(superclass_content)
    subclass_file.write_text(subclass_content)

    # Add tmp_path to sys.path and set up CustomFinder
    sys.path.insert(0, str(tmp_path))

    SubclassExtensionPoints().initialize()

    try:
        # Import the superclass module
        superclass_module = importlib.import_module("superclass_registry_module")

        # Add TestSuperClassForRegistry to the whitelist
        add_to_whitelist(superclass_module.TestSuperClassForRegistry)

        # Register a callback for TestSuperClassForRegistry
        def callback(cls):
            pass

        superclass_module.TestSuperClassForRegistry = register_superclass_callback(
            superclass_module.TestSuperClassForRegistry, callback)

        # Check if TestSuperClassForRegistry is in the registry
        super_key = (
            superclass_module.TestSuperClassForRegistry.__module__,
            superclass_module.TestSuperClassForRegistry.__name__)
        assert super_key in subclass_registry, "TestSuperClassForRegistry should be in the registry"

        # Import the subclass module
        subclass_module = importlib.import_module("subclass_registry_module")

        # Check if TestSubClassForRegistry uses SubclassDetectingMeta
        assert isinstance(subclass_module.TestSubClassForRegistry,
                          SubclassDetectingMeta), "TestSubClassForRegistry should use SubclassDetectingMeta"

        # Check if TestSubClassForRegistry triggered the callback (i.e., it's in the registry)
        sub_key = (subclass_module.TestSubClassForRegistry.__module__, subclass_module.TestSubClassForRegistry.__name__)
        assert any(sub_key == key or issubclass(subclass_module.TestSubClassForRegistry, superclass)
                   for key, callbacks in subclass_registry.items()
                   for superclass in [getattr(sys.modules.get(key[0]), key[1], None)]
                   if
                   superclass is not None), "TestSubClassForRegistry should be in the registry or be a subclass of a registered class"

    finally:
        # Clean up
        sys.path.pop(0)
        sys.meta_path.pop(0)


def test_skips_special_classes():
    apply_subclass_detecting_metaclass(ObjectProxy)
    apply_subclass_detecting_metaclass(SchemaValidator)
