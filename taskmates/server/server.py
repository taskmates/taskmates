import asyncio

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import Quart

from taskmates import logging, root_path
from taskmates.config.find_config_file import find_config_file
from taskmates.config.load_participant_config import load_yaml_config
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


@app.route('/v1/models', methods=['GET'])
async def list_models():
    # Load models from the configuration
    taskmates_dirs = [
        root_path() / "taskmates/defaults"
    ]
    config_path = find_config_file("models.yaml", taskmates_dirs)
    if config_path is None:
        return {"error": "models.yaml not found"}, 404

    model_config = load_yaml_config(config_path) or {}

    return {"models": model_config}, 200


if __name__ == "__main__":
    auto_instrument()

    import hypercorn.asyncio

    config = hypercorn.Config.from_mapping(bind="localhost:55000", use_reloader=True)
    asyncio.run(hypercorn.asyncio.serve(app, config), debug=True)
