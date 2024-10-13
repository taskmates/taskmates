from taskmates.workflow_engine.run import Run
from taskmates.lib.opentelemetry_.wrap_module import wrap_module
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


# Usage:


def instrument():
    SubclassExtensionPoints.subscribe(Run, wrap_module)
