import contextlib
from typing import Callable, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer

from taskmates.lib.opentelemetry_.add_span_attributes import add_span_attributes
from taskmates.lib.opentelemetry_.format_span_name import format_span_name

tracer: Tracer = trace.get_tracer_provider().get_tracer(__name__)


def _create_trace_wrapper(is_async: False,
                          wrapped_module: None,
                          span_name_fn: Callable[[Callable, Any, tuple[Any],
                                                  dict[str, Any]], str] | None = None) -> Callable:
    async def async_traced_call(wrapped, instance, args, kwargs):
        with traced_call(wrapped, instance, args, kwargs) as span:
            result = await wrapped(*args, **kwargs)
            if span.is_recording():
                span.set_attribute("call.return", repr(result))
            return result

    def sync_traced_call(wrapped, instance, args, kwargs):
        with traced_call(wrapped, instance, args, kwargs) as span:
            result = wrapped(*args, **kwargs)
            if span.is_recording():
                span.set_attribute("call.return", repr(result))
            return result

    @contextlib.contextmanager
    def traced_call(wrapped, instance, args, kwargs):
        if span_name_fn is not None:
            span_name = span_name_fn(wrapped, instance, args, kwargs)
        else:
            span_name = format_span_name(wrapped, instance, wrapped_module)

        with tracer.start_as_current_span(span_name, kind=trace.SpanKind.INTERNAL) as span:
            try:
                if span.is_recording():
                    add_span_attributes(span, wrapped, instance, args, kwargs)
                yield span
            except Exception:
                raise

    if is_async:
        return async_traced_call
    else:
        return sync_traced_call
