import asyncio

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import Quart

from taskmates import logging
from taskmates.lib.opentelemetry_.tracing import auto_instrument
from taskmates.server.blueprints.api_completions import completions_bp as completions_v2_bp
from taskmates.server.blueprints.echo import echo_pb
from taskmates.server.blueprints.health import health_bp
from taskmates.server.blueprints.kernel_status import kernel_status_bp

app = Quart(__name__)
app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
app.logger.setLevel(logging.level)

app.register_blueprint(completions_v2_bp)
app.register_blueprint(echo_pb)
app.register_blueprint(health_bp)
app.register_blueprint(kernel_status_bp)

if __name__ == "__main__":
    auto_instrument()

    import hypercorn.asyncio

    config = hypercorn.Config.from_mapping(bind="localhost:55000", use_reloader=True)
    asyncio.run(hypercorn.asyncio.serve(app, config), debug=True)
