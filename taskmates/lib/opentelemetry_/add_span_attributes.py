import inspect

from opentelemetry.semconv.trace import SpanAttributes


def add_span_attributes(span, wrapped, instance, args, kwargs):
    callee_class = instance.__class__ if not inspect.isclass(instance) else instance
    span.set_attribute(SpanAttributes.CODE_FUNCTION, wrapped.__name__)
    span.set_attribute(SpanAttributes.CODE_NAMESPACE, callee_class.__name__)
    span.set_attribute("call.instance", repr(instance))
    # turn each arg into a call.argN attribute
    for i, arg in enumerate(args):
        span.set_attribute(f"call.args.{i}", repr(arg))
    # turn each karg into a call.kargN attribute
    for i, (k, v) in enumerate(kwargs.items()):
        span.set_attribute(f"call.kargs.{k}", repr(v))
