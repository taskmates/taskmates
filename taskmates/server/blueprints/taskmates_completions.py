import asyncio
import json

from quart import Blueprint, Response
from quart import websocket

import taskmates
from taskmates.config.client_config import CLIENT_CONFIG
from taskmates.config.completion_context import COMPLETION_CONTEXT, CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS, CompletionOpts
from taskmates.config.server_config import SERVER_CONFIG
from taskmates.config.updated_config import updated_config
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.file_system_artifacts_sink import FileSystemArtifactsSink
from taskmates.io.websocket_completion_streamer import WebsocketCompletionStreamer
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


async def handle_interrupt_or_kill(websocket, signals: Signals):
    while True:
        try:
            raw_payload = await websocket.receive()
            payload = snake_case(json.loads(raw_payload))
            if payload.get("type") == "interrupt":
                await signals.control.interrupt_request.send_async(None)
            elif payload.get("type") == "kill":
                logger.info(f"KILL Received kill message")
                await signals.control.kill.send_async(None)
        except asyncio.CancelledError:
            break


@completions_bp.websocket('/v2/taskmates/completions')
async def taskmates_completions():
    signals = Signals()
    SIGNALS.set(signals)

    receive_interrupt_task = None
    completion_task = None

    # TODO
    WebsocketCompletionStreamer().connect(signals)

    try:
        logger.info("Waiting for websocket connsection at /v2/taskmates/completions")
        raw_payload = await websocket.receive()
        payload: CompletionPayload = snake_case(json.loads(raw_payload))

        client_version = payload.get("version", "None")
        if client_version != taskmates.__version__:
            raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

        # --- Config ---

        server_config = SERVER_CONFIG.get()
        taskmates_dir = server_config["taskmates_dir"]
        completion_context: CompletionContext = payload["completion_context"]
        completion_opts: CompletionOpts = payload["completion_opts"]
        markdown_chat = payload["markdown_chat"]
        request_id = completion_context['request_id']

        # --- Bind ---

        # TODO
        FileSystemArtifactsSink(taskmates_dir, request_id).connect(signals)

        with updated_config(COMPLETION_CONTEXT, completion_context), \
                updated_config(COMPLETION_OPTS, completion_opts):

            logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

            await signals.output.artifact.send_async({"name": "websockets_api_payload.json", "content": payload})

            receive_interrupt_task = asyncio.create_task(handle_interrupt_or_kill(websocket, signals))

            # --- Execute ---

            completion_task = asyncio.create_task(
                CompletionEngine().perform_completion(completion_context,
                                                      markdown_chat,
                                                      SERVER_CONFIG.get(),
                                                      CLIENT_CONFIG.get(),
                                                      COMPLETION_OPTS.get(),
                                                      signals)
            )

            completion_task.add_done_callback(lambda t: receive_interrupt_task.cancel("Completion Task Finished"))

            done, pending = await asyncio.wait([receive_interrupt_task, completion_task],
                                               return_when=asyncio.ALL_COMPLETED)
            logger.info(f"AWAIT Await finished")

            # Raise exception if any task failed
            for task in done:
                task.result()

    except asyncio.CancelledError:
        logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
        await signals.control.kill.send_async(None)
    except Exception as e:
        # logger.exception(e)
        await signals.response.error.send_async(e)
    finally:
        # --- Clean up ---
        if receive_interrupt_task and not receive_interrupt_task.done():
            receive_interrupt_task.cancel()
        if completion_task and not completion_task.done():
            completion_task.cancel()
        logger.info("DONE Closing websocket connection")


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info(f'Request Finished.')
