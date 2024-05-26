import functools
import logging
import os

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import NoOpTracerProvider
from taskmates.lib.opentelemetry_.async_start_as_current_span import async_start_as_current_span

# NOTE: Usage
# with tracer.start_as_current_span(span_name, kind=trace.SpanKind.INTERNAL) as span:

resource = Resource(attributes={
    SERVICE_NAME: "internal"
})

# Check if tracing is enabled via environment variable
enable_tracing = os.getenv('TASKMATES_TELEMETRY_ENABLED', 'false').lower() in ['true', '1', 't']

# If tracing is enabled, configure the tracer provider with OTLP exporter
# Otherwise, use NoopTracerProvider to effectively disable tracing
if enable_tracing:
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(1.0)  # Sample all traces
    )
    tracer_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
    tracer_provider.add_span_processor(tracer_processor)
    trace.set_tracer_provider(tracer_provider)

    # Configure logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    log_exporter = OTLPLogExporter(endpoint="http://localhost:4317")
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    logging_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(logging_handler)
else:
    # No-op TracerProvider which will cause all operations to be no-op
    trace.set_tracer_provider(NoOpTracerProvider())

# Configure metrics
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317")
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer("taskmates")

tracer.async_start_as_current_span = functools.partial(async_start_as_current_span, tracer)

# Configure logging
LoggingInstrumentor().instrument(set_logging_format=True)
