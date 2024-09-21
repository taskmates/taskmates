from taskmates.core.job import Job
from taskmates.lib.opentelemetry_.wrap_module import wrap_module
from taskmates.sdk.experimental.subclass_extension_points import SubclassExtensionPoints


# Usage:


def instrument():
    SubclassExtensionPoints.subscribe(Job, wrap_module)
