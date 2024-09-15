import inspect
import re
from typing import Optional, Callable, Any

from wrapt import resolve_path, wrap_function_wrapper

from taskmates.lib.opentelemetry_._create_trace_wrapper import _create_trace_wrapper
from taskmates.lib.opentelemetry_.default_exclusions import global_exclude_modules_regex
from taskmates.lib.opentelemetry_.tracing import tracer


def wrap_function(module,
                  name: str,
                  exclude_modules_regex: Optional[list] = None,
                  span_name_fn: Callable[[Callable, Any, tuple[Any], dict[str, Any]], str] | None = None):
    if exclude_modules_regex is None:
        exclude_modules_regex = []
    if any(re.match(regex, module.__name__) for regex in (global_exclude_modules_regex + exclude_modules_regex)):
        return

    (parent, attribute, original) = resolve_path(module, name)

    if hasattr(original, "_wrapped_with_tracer"):
        return

    is_async = inspect.iscoroutinefunction(getattr(module, name))
    function_wrapper = wrap_function_wrapper(module=module,
                                             name=name,
                                             wrapper=_create_trace_wrapper(tracer(),
                                                                           is_async,
                                                                           wrapped_module=module,
                                                                           span_name_fn=span_name_fn))
    function_wrapper._wrapped_with_tracer = True

    # if hasattr(module, "__subclasses__"):
    #     for subclass in module.__subclasses__():
    #         # TODO
    #         # register_superclass_callback(module, lambda subclass: print("Detected subclass", subclass))
    #         wrap_function(subclass, name, exclude_modules_regex=exclude_modules_regex, span_name_fn=span_name_fn)
