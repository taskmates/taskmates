import asyncio

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import Quart

from taskmates import env, logging
from taskmates.server.blueprints.echo import echo_pb
from taskmates.server.blueprints.health import health_bp
from taskmates.server.blueprints.completions_api import completions_bp as completions_v2_bp
from taskmates.sdk import PluginManager

env.bootstrap()

app = Quart(__name__)
app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
app.logger.setLevel(logging.level)

plugin_manager = PluginManager()

@app.before_serving
async def setup_plugins():
    plugin_manager.load_plugins()
    await plugin_manager.initialize_plugins(app)

app.register_blueprint(completions_v2_bp)
app.register_blueprint(echo_pb)
app.register_blueprint(health_bp)

if __name__ == "__main__":
    import hypercorn.asyncio

    config = hypercorn.Config.from_mapping(bind="localhost:55000", use_reloader=True)
    asyncio.run(hypercorn.asyncio.serve(app, config), debug=True)
