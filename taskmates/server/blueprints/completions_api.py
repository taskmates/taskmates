import asyncio
import json

from quart import Blueprint, Response, websocket

import taskmates
from taskmates.core.completion_engine import CompletionEngine
from taskmates.io.file_system_artifacts_sink import FileSystemArtifactsSink
from taskmates.io.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.io.web_socket_interrupt_and_kill_controller import WebSocketInterruptAndKillController
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.server.blueprints.build_context import build_context
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


@completions_bp.websocket('/v2/taskmates/completions')
async def create_completion():
    handlers = [
        WebSocketInterruptAndKillController(websocket),
        WebSocketCompletionStreamer(websocket),
        FileSystemArtifactsSink(),  # TODO: this should be disabled by default
    ]

    with temp_context(SIGNALS, Signals()) as signals, \
            signals.connected_to(handlers):
        try:
            logger.info("Waiting for websocket connection at /v2/taskmates/completions")
            raw_payload = await websocket.receive()

            payload: CompletionPayload = snake_case(json.loads(raw_payload))
            request_id = payload['completion_context']['request_id']
            logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

            client_version = payload.get("version", "None")
            if client_version != taskmates.__version__:
                raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

            with build_context(payload) as context:
                markdown_chat = payload["markdown_chat"]

                await signals.output.artifact.send_async({"name": "websockets_api_payload.json", "content": payload})

                result = await CompletionEngine().perform_completion(
                    markdown_chat,
                    [],
                    context,
                    signals
                )

                return result

        # TODO: remove after we properly tested client disconnect
        except asyncio.CancelledError:
            logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
            await signals.control.kill.send_async({})
        except Exception as e:
            await signals.response.error.send_async(e)
        finally:
            logger.info("DONE Closing websocket connection")


@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info(f'Request Finished.')
