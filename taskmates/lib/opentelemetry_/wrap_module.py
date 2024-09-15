import re
from typing import Optional, Callable, Any

from taskmates.lib.inspect_.get_methods import get_methods
from taskmates.lib.opentelemetry_.default_exclusions import global_exclude_methods_regex
from taskmates.lib.opentelemetry_.wrap_function import wrap_function


def wrap_module(module,
                exclude_modules_regex: Optional[list] = None,
                exclude_methods_regex: Optional[list] = None,
                span_name_fn: Callable[[Callable, Any, tuple[Any], dict[str, Any]], str] | None = None):
    if exclude_modules_regex is None:
        exclude_modules_regex = []
    if exclude_methods_regex is None:
        exclude_methods_regex = []
    methods = get_methods(module)

    methods = [method for method in methods if
               not any(re.match(regex, method) for regex in (global_exclude_methods_regex + exclude_methods_regex))]

    for method in methods:
        wrap_function(module, method, exclude_modules_regex=exclude_modules_regex, span_name_fn=span_name_fn)
