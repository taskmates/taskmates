from typing import Dict, Type, Callable, List, TypedDict, is_typeddict, Set

import builtins
import pytest
from loguru import logger
from pydantic_core import SchemaValidator
from wrapt import ObjectProxy


class SubclassExtensionPoints:
    # Registry to hold superclasses and their list of callbacks
    superclass_registry: Dict[type, List[Callable[[Type], None]]] = {}

    # Whitelist for classes that should be instrumented
    class_whitelist: Set[Type] = set()

    @classmethod
    def custom_build_class(cls, func, name, *bases, **kwargs):
        new_class = cls.original_build_class(func, name, *bases, **kwargs)
        return cls.class_created_hook(new_class)

    @classmethod
    def class_created_hook(cls, new_class):
        for superclass in cls.superclass_registry:
            if issubclass(new_class, superclass):
                logger.debug(f"Detected subclass {new_class.__name__} of {superclass.__name__}")
                for callback in cls.superclass_registry[superclass]:
                    callback(new_class)
        return new_class

    @classmethod
    def subscribe(cls, superclass: Type, handler: Callable[[Type], None]):
        """Register a callback to be called when a subclass of the given superclass is created."""
        if not cls.should_instrument_class(superclass):
            raise TypeError(f"Cannot register callbacks for {superclass.__name__} classes")

        if superclass not in cls.superclass_registry:
            cls.superclass_registry[superclass] = []

        logger.debug(f"Registering callback for {superclass.__name__}")
        cls.superclass_registry[superclass].append(handler)
        return superclass

    @classmethod
    def add_to_whitelist(cls, class_to_add: Type):
        """Add a class to the whitelist for instrumentation."""
        cls.class_whitelist.add(class_to_add)

    @classmethod
    def should_instrument_class(cls, class_to_check):
        if not isinstance(class_to_check, type):
            return False

        if class_to_check in cls.class_whitelist:
            return True

        if "taskmates" not in class_to_check.__module__:
            return False

        return isinstance(class_to_check, type) and type(class_to_check).__name__ in ('type', 'ABCMeta')

    @classmethod
    def initialize(cls):
        logger.debug("Initializing SubclassExtensionPoints")
        if hasattr(cls, "original_build_class") and cls.original_build_class:
            return
        cls.superclass_registry.clear()
        cls.class_whitelist.clear()
        cls.original_build_class = builtins.__build_class__
        builtins.__build_class__ = cls.custom_build_class

    @classmethod
    def cleanup(cls):
        logger.debug(f"Cleaning up SubclassExtensionPoints {cls.original_build_class}")
        if hasattr(cls, "original_build_class") and cls.original_build_class:
            builtins.__build_class__ = cls.original_build_class
            cls.original_build_class = None


# Tests
# TODO: this is already done by the taskmates_runtime fixture. Figure out a way to remove this duplication
# @pytest.fixture(autouse=True)
# def setup_extension_points():
#     try:
#         SubclassExtensionPoints.initialize()
#         yield
#     finally:
#         SubclassExtensionPoints.cleanup()


def test_register_superclass_callback():
    class TestSuperClass:
        pass

    SubclassExtensionPoints.add_to_whitelist(TestSuperClass)

    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    SubclassExtensionPoints.subscribe(TestSuperClass, callback)

    assert TestSuperClass in SubclassExtensionPoints.superclass_registry
    assert callback in SubclassExtensionPoints.superclass_registry[TestSuperClass]

    class TestSubClass(TestSuperClass):
        pass

    assert callback_called, "Callback was not called when subclass was created"


def test_typed_dict_handling():
    class MyTypedDict(TypedDict):
        name: str
        age: int

    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    with pytest.raises(TypeError, match="Cannot register callbacks for MyTypedDict classes"):
        SubclassExtensionPoints.subscribe(MyTypedDict, callback)

    assert is_typeddict(MyTypedDict), "MyTypedDict should remain a TypedDict"

    class ExtendedTypedDict(MyTypedDict):
        extra: bool

    assert is_typeddict(ExtendedTypedDict), "ExtendedTypedDict should remain a TypedDict"

    assert not callback_called, "Callback should not have been called for TypedDict subclassing"


def test_skips_special_classes():
    SubclassExtensionPoints.class_created_hook(ObjectProxy)
    SubclassExtensionPoints.class_created_hook(SchemaValidator)
