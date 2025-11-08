import json

from quart import Blueprint, Response, websocket

import taskmates
from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflow_engine.objective import ObjectiveKey, Objective
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import file_logger
from taskmates.logging import logger
from taskmates.core.workflows.markdown_completion.markdown_completion import MarkdownCompletion
from taskmates.runtimes.api.websocket_bindings import WebsocketBindings
from taskmates.runtimes.api.api_context_builder import ApiContextBuilder
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

    file_logger.debug("websockets_api_payload.json", content=payload)

    transaction = Transaction(
        objective=Objective(
            key=ObjectiveKey(
                outcome="ApiCompletionTransaction",
                inputs={"markdown_chat": payload["markdown_chat"]}
            )
        ),
        context=ApiContextBuilder(payload).build()
    )

    async with WebsocketBindings(transaction, websocket):
        markdown_completion_transaction = transaction.create_bound_transaction(
            operation=MarkdownCompletion().fulfill,
            inputs={"markdown_chat": payload["markdown_chat"]},
            result_format={'format': 'completion', 'interactive': True}
        )

        return await markdown_completion_transaction()


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info('Request Finished.')
