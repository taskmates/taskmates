import json

from quart import Blueprint, Response, websocket

import taskmates
from taskmates.context_builders.api_context_builder import ApiContextBuilder
from taskmates.core.io.emitters.web_socket_interrupt_and_kill_controller import WebSocketInterruptAndKillController
from taskmates.core.io.listeners.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.defaults.workflows.api_complete import ApiComplete
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


@completions_bp.before_app_serving
async def before_app_serving():
    TASKMATES_RUNTIME.get().initialize()


@completions_bp.websocket('/v2/taskmates/completions')
async def create_completion():
    logger.info("Waiting for websocket connection at /v2/taskmates/completions")
    raw_payload = await websocket.receive()

    payload: CompletionPayload = snake_case(json.loads(raw_payload))
    request_id = payload['completion_context']['request_id']
    logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

    client_version = payload.get("version", "None")
    if client_version != taskmates.__version__:
        raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

    jobs = [
        WebSocketInterruptAndKillController(websocket),
        WebSocketCompletionStreamer(websocket),
    ]

    contexts = ApiContextBuilder(payload).build()
    return await ApiComplete(contexts=contexts, jobs=jobs).run(payload=payload)


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info(f'Request Finished.')
