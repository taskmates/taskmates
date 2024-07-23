import asyncio
import json
from contextlib import contextmanager

from quart import Blueprint, Response, websocket
from typeguard import typechecked

import taskmates
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import COMPLETION_CONTEXT, CompletionContext
from taskmates.config.completion_opts import COMPLETION_OPTS, CompletionOpts
from taskmates.config.server_config import SERVER_CONFIG
from taskmates.config.updated_config import updated_config
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.file_system_artifacts_sink import FileSystemArtifactsSink
from taskmates.io.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.io.web_socket_interrupt_and_kill_handler import WebSocketInterruptAndKillHandler
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


@typechecked
@contextmanager
def build_context(payload: CompletionPayload):
    completion_context: CompletionContext = payload["completion_context"]
    completion_opts: CompletionOpts = payload["completion_opts"]

    # Ensure template_params is present in completion_opts
    if "template_params" not in completion_opts:
        completion_opts["template_params"] = {}

    client_config = ClientConfig(interactive=True,
                                 format="completion", )

    server_config = SERVER_CONFIG.get()

    with updated_config(COMPLETION_CONTEXT, completion_context), \
            updated_config(COMPLETION_OPTS, completion_opts):
        yield {
            'context': COMPLETION_CONTEXT.get(),
            'client_config': client_config,
            'server_config': server_config,
            'completion_opts': COMPLETION_OPTS.get()
        }


@completions_bp.websocket('/v2/taskmates/completions')
async def taskmates_completions():
    signals = Signals()
    SIGNALS.set(signals)

    server_config = SERVER_CONFIG.get()
    taskmates_dir = server_config["taskmates_dir"]

    websocket_handler = WebSocketCompletionStreamer(websocket)
    interrupt_handler = WebSocketInterruptAndKillHandler(websocket)
    handlers = [
        websocket_handler,
        interrupt_handler,
    ]

    # Connect handlers
    for handler in handlers:
        handler.connect(signals)

    try:
        logger.info("Waiting for websocket connection at /v2/taskmates/completions")
        raw_payload = await websocket.receive()
        payload: CompletionPayload = snake_case(json.loads(raw_payload))

        client_version = payload.get("version", "None")
        if client_version != taskmates.__version__:
            raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

        with build_context(payload) as context:
            request_id = context['context']['request_id']
            markdown_chat = payload["markdown_chat"]

            # Add FileSystemArtifactsSink as a handler
            file_system_handler = FileSystemArtifactsSink(taskmates_dir, request_id)
            file_system_handler.connect(signals)
            handlers.append(file_system_handler)

            await signals.output.artifact.send_async({"name": "websockets_api_payload.json", "content": payload})

            logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

            result = await CompletionEngine().perform_completion(
                context['context'],
                markdown_chat,
                context['server_config'],
                context['client_config'],
                context['completion_opts'],
                signals
            )

            return result

    except asyncio.CancelledError:
        logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
        await signals.control.kill.send_async({})
    except Exception as e:
        await signals.response.error.send_async(e)
    finally:
        # Disconnect handlers
        for handler in handlers:
            handler.disconnect(signals)
        logger.info("DONE Closing websocket connection")


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info(f'Request Finished.')
