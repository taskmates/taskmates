import inspect


def format_span_name(wrapped, instance, wrapped_module=None):
    declaring_module = "" if wrapped_module is None or wrapped_module == instance.__class__ else f"({wrapped_module.__name__})"

    is_instance_method = not inspect.isclass(instance)
    callee_class = instance.__class__ if is_instance_method else instance
    method_separator = "#" if is_instance_method else "."

    # Example: SignalsCapturer@5408743568#filter_signals
    # span_name = f"{callee_class.__name__}@{id(instance)}{method_separator}{declaring_module}{wrapped.__name__}"

    # Example: filter_signals [SignalsCapturer@5408743568]

    span_name = f"{wrapped.__name__} [{callee_class.__name__}{declaring_module}@{id(instance)}]"

    if hasattr(instance, "resolve"):
        span_name = f"RESOLVE {instance.__class__.__name__}[{instance.referencekey}]"
    return span_name
