import contextlib
import inspect
from typing import Callable, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer
from opentelemetry.semconv.trace import SpanAttributes


def _create_trace_wrapper(tracer: Tracer, is_async: False, wrapper_origin: None,
                          span_name_fn: Callable[[Callable, Any, tuple[Any],
                                                  dict[str, Any]], str] | None = None) -> Callable:
    async def async_traced_call(func, instance, args, kwargs):
        with traced_call(func, instance, args, kwargs) as span:
            result = await func(*args, **kwargs)
            if span.is_recording(): span.set_attribute(f"call.return", repr(result))
            return result

    def sync_traced_call(func, instance, args, kwargs):
        with traced_call(func, instance, args, kwargs) as span:
            result = func(*args, **kwargs)
            if span.is_recording():  span.set_attribute(f"call.return", repr(result))
            return result

    @contextlib.contextmanager
    def traced_call(func, instance, args, kwargs):
        wrapped_module = wrapper_origin
        declaring_module = "" if wrapped_module is None or wrapped_module == instance.__class__ else f"({wrapped_module.__name__})"
        is_instance_method = not inspect.isclass(instance)
        callee_class = instance.__class__ if is_instance_method else instance
        method_separator = "#" if is_instance_method else "."

        if span_name_fn is not None:
            span_name = span_name_fn(func, instance, args, kwargs)
        else:
            span_name = f"{callee_class.__name__}@{id(instance)}{method_separator}{declaring_module}{func.__name__}"

        if hasattr(instance, "resolve"):
            span_name = f"RESOLVE {instance.__class__.__name__}[{instance.referencekey}]"

        with tracer.start_as_current_span(span_name, kind=trace.SpanKind.INTERNAL) as span:
            try:
                if span.is_recording():
                    span.set_attribute(SpanAttributes.CODE_FUNCTION, func.__name__)
                    span.set_attribute(SpanAttributes.CODE_NAMESPACE, callee_class.__name__)
                    span.set_attribute("call.instance", repr(instance))

                    # turn each arg into a call.argN attribute
                    for i, arg in enumerate(args):
                        span.set_attribute(f"call.args.{i}", repr(arg))

                    # turn each karg into a call.kargN attribute
                    for i, (k, v) in enumerate(kwargs.items()):
                        span.set_attribute(f"call.kargs.{k}", repr(v))

                yield span
            except Exception:
                raise

    if is_async:
        return async_traced_call
    else:
        return sync_traced_call
