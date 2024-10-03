from taskmates.core.execution_context import ExecutionContext
from taskmates.lib.opentelemetry_.wrap_module import wrap_module
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


# Usage:


def instrument():
    SubclassExtensionPoints.subscribe(ExecutionContext, wrap_module)
