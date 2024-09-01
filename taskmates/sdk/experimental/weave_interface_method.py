from wrapt import wrap_function_wrapper

from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


def weave_interface_method(cls, function_name, handler):
    SubclassExtensionPoints.subscribe(cls,
                                      lambda new_subclass: wrap_function_wrapper(new_subclass, function_name,
                                                                                 handler))
    for existing_subclass in cls.__subclasses__():
        wrap_function_wrapper(existing_subclass, function_name, handler)
