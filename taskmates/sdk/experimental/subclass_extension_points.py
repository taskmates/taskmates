from typing import Dict, Type, Callable, List, TypedDict, is_typeddict, Tuple

import builtins
from loguru import logger
from pydantic_core import SchemaValidator
from wrapt import ObjectProxy


def is_taskmates_code(class_to_check):
    return "taskmates" in class_to_check.__module__


class SubclassExtensionPoints:
    # Registry to hold superclasses, their list of callbacks, and criteria
    selectors: Dict[type, List[Tuple[Callable[[Type], None], Callable[[Type], bool]]]] = {}

    @classmethod
    def _custom_build_class(cls, func, name, *bases, **kwargs):
        new_class = cls.original_build_class(func, name, *bases, **kwargs)
        return cls._class_created_hook(new_class)

    @classmethod
    def _class_created_hook(cls, new_class):
        for superclass, callbacks_and_criteria in cls.selectors.items():
            if is_typeddict(superclass) and is_typeddict(new_class):
                # Special handling for TypedDict
                if issubclass(new_class, dict) and issubclass(superclass, dict):
                    logger.debug(f"Detected TypedDict subclass {new_class.__name__} of {superclass.__name__}")
                    for callback, criteria in callbacks_and_criteria:
                        if criteria(new_class):
                            callback(new_class)
            elif issubclass(new_class, superclass):
                logger.debug(f"Detected subclass {new_class.__name__} of {superclass.__name__}")
                for callback, criteria in callbacks_and_criteria:
                    if criteria(new_class):
                        callback(new_class)
        return new_class

    @classmethod
    def subscribe(cls, superclass: Type,
                  handler: Callable[[Type], None],
                  filter_fn: Callable[[Type], bool] = is_taskmates_code):
        """Register a callback to be called when a subclass of the given superclass is created."""

        if not isinstance(superclass, type):
            raise TypeError(f"Cannot register callbacks for {superclass.__name__} classes")

        if superclass not in cls.selectors:
            cls.selectors[superclass] = []

        logger.debug(f"Registering callback for {superclass.__name__}")
        cls.selectors[superclass].append((handler, filter_fn))

        if filter_fn(superclass):
            handler(superclass)
        for subclass in superclass.__subclasses__():
            if filter_fn(subclass):
                handler(subclass)

        return superclass

    @classmethod
    def initialize(cls):
        logger.debug("Initializing SubclassExtensionPoints")
        if hasattr(cls, "original_build_class") and cls.original_build_class:
            return
        cls.selectors.clear()
        cls.original_build_class = builtins.__build_class__
        builtins.__build_class__ = cls._custom_build_class

    @classmethod
    def cleanup(cls):
        logger.debug(f"Cleaning up SubclassExtensionPoints {cls.original_build_class}")
        if hasattr(cls, "original_build_class") and cls.original_build_class:
            builtins.__build_class__ = cls.original_build_class
            cls.original_build_class = None


# Tests
def test_register_superclass_callback():
    class TestSuperClass:
        pass

    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    SubclassExtensionPoints.subscribe(TestSuperClass, callback, filter_fn=lambda cls: True)

    assert TestSuperClass in SubclassExtensionPoints.selectors
    assert callback in [cb for cb, _ in SubclassExtensionPoints.selectors[TestSuperClass]]

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

    SubclassExtensionPoints.subscribe(MyTypedDict, callback, filter_fn=lambda cls: True)

    assert is_typeddict(MyTypedDict), "MyTypedDict should remain a TypedDict"

    class ExtendedTypedDict(MyTypedDict):
        extra: bool

    assert is_typeddict(ExtendedTypedDict), "ExtendedTypedDict should remain a TypedDict"
    assert callback_called, "Callback should have been called for TypedDict subclassing"


def test_skips_special_classes():
    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    SubclassExtensionPoints.subscribe(object, callback, filter_fn=lambda cls: False)

    SubclassExtensionPoints._class_created_hook(ObjectProxy)
    SubclassExtensionPoints._class_created_hook(SchemaValidator)

    assert not callback_called, "Callback should not have been called for special classes"


def test_default_criteria():
    class TestSuperClass:
        pass

    class TestSubClass(TestSuperClass):
        pass

    TestSubClass.__module__ = "some_module"
    TestSuperClass.__module__ = "some_module"

    callback_called = False

    def callback(cls):
        nonlocal callback_called
        callback_called = True

    SubclassExtensionPoints.subscribe(TestSuperClass, callback)

    assert not callback_called, "Callback should not have been called when default criteria is not met"

    TestSubClass.__module__ = "taskmates.some_module"
    SubclassExtensionPoints._class_created_hook(TestSubClass)

    assert callback_called, "Callback should have been called when default criteria is met"
