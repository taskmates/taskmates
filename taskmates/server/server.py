import asyncio

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import Quart

from taskmates import env, logging
from taskmates.server.blueprints.echo import echo_pb
from taskmates.server.blueprints.health import health_bp
from taskmates.server.blueprints.taskmates_completions import completions_bp as completions_v2_bp

env.bootstrap()

app = Quart(__name__)
app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
# from quart_cors import cors
# app = cors(app, allow_origin="*")  # Allow requests from any origin
app.logger.setLevel(logging.level)

app.register_blueprint(completions_v2_bp)
app.register_blueprint(echo_pb)
app.register_blueprint(health_bp)

if __name__ == "__main__":
    import hypercorn.asyncio

    config = hypercorn.Config.from_mapping(bind="localhost:55000", use_reloader=True)
    asyncio.run(hypercorn.asyncio.serve(app, config), debug=True)

# async def shutdown():
#     print("SHUTDOWN CALLED")
#     print("FOOOOOOO")
#
# #     # Close all WebSocket connections here
# #     for ws in app.websocket_manager.connections:
# #         await ws.close()
# #
# # if __name__ == "__main__":
# #     config = Config.from_mapping(bind="localhost:55000", reload=True)
#
# def handle_shutdown_signal(*args):
#     asyncio.run(shutdown())
#     sys.exit(0)
#
#
# if __name__ == "__main__":
#     import signal
#     from hypercorn.config import Config
#     from hypercorn.asyncio import serve
#
#     config = Config.from_mapping(bind="localhost:55000", reload=True, use_reloader=True, shutdown_timeout=1)
#     signal.signal(signal.SIGTERM, handle_shutdown_signal)
#     signal.signal(signal.SIGINT, handle_shutdown_signal)
#
#     try:
#         loop = asyncio.get_event_loop()
#         # loop.run_until_complete(serve(app, config, shutdown_trigger=shutdown))
#         loop.run_until_complete(serve(app, config))
#     except KeyboardInterrupt:
#         asyncio.run(shutdown())
#         print("KEYBOARD_INTERRUPT")
