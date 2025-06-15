import json

from quart import Blueprint, Response, websocket

import taskmates
from taskmates.runtimes.api.api_completion_runner import ApiCompletionRunner
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.taskmates_runtime import TASKMATES_RUNTIME
from taskmates.types import ApiRequest

completions_bp = Blueprint('completions_v2', __name__)


@completions_bp.before_app_serving
async def before_app_serving():
    TASKMATES_RUNTIME.get().initialize()


@completions_bp.websocket('/v2/taskmates/completions')
async def create_completion():
    logger.info("Waiting for websocket connection at /v2/taskmates/completions")
    raw_payload = await websocket.receive()

    payload: ApiRequest = snake_case(json.loads(raw_payload))
    request_id = payload['runner_environment']['request_id']
    logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

    client_version = payload.get("version", "None")
    if client_version != taskmates.__version__:
        raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

    return await ApiCompletionRunner(websocket=websocket).run(payload=payload)


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info('Request Finished.')
