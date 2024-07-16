import asyncio
import json

from quart import Blueprint, Response
from quart import websocket

import taskmates
from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionContext, CompletionOpts, COMPLETION_CONTEXT, COMPLETION_OPTS, \
    updated_config, SERVER_CONFIG
from taskmates.lib.json_.json_utils import snake_case
from taskmates.logging import logger
from taskmates.signals.signals import SIGNALS, Signals
from taskmates.sinks.file_system_artifacts_sink import FileSystemArtifactsSink
from taskmates.bridges.websocket_bridges import SignalToWebsocketBridge, WebsocketToSignalBridge
from taskmates.sinks.websocket_streaming_sink import WebsocketSignalBridge
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


@completions_bp.websocket('/v2/taskmates/completions')
async def taskmates_completions():
    signals = Signals()
    SIGNALS.set(signals)

    receive_interrupt_task = None
    completion_task = None

    try:
        logger.info("Waiting for websocket connection at /v2/taskmates/completions")
        raw_payload = await websocket.receive()

        payload: CompletionPayload = snake_case(json.loads(raw_payload))

        client_version = payload.get("version", "None")
        if client_version != taskmates.__version__:
            raise ValueError(f"Incompatible client version: {client_version}. Expected: {taskmates.__version__}")

        server_config = SERVER_CONFIG.get()
        taskmates_dir = server_config["taskmates_dir"]

        completion_context: CompletionContext = payload["completion_context"]
        completion_opts: CompletionOpts = payload["completion_opts"]
        markdown_chat = payload["markdown_chat"]
        request_id = completion_context['request_id']

        WebsocketSignalBridge().connect(signals)
        FileSystemArtifactsSink(taskmates_dir, request_id).connect(signals)

        with updated_config(COMPLETION_CONTEXT, completion_context), \
                updated_config(COMPLETION_OPTS, completion_opts):
            logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

            await signals.output.artifact.send_async({"name": "websockets_api_payload.json", "content": payload})

            async def handle_interrupt_or_kill():
                while True:
                    try:
                        raw_payload = await websocket.receive()
                        payload = snake_case(json.loads(raw_payload))
                        if payload.get("type") == "interrupt":
                            await signals.control.interrupt_request.send_async(None)
                        elif payload.get("type") == "kill":
                            logger.info(f"KILL Received kill message for request {request_id}")
                            await signals.control.kill.send_async(None)
                    except asyncio.CancelledError:
                        break

            receive_interrupt_task = asyncio.create_task(handle_interrupt_or_kill())

            completion_task = asyncio.create_task(
                MarkdownCompletionAssistance().perform_completion(completion_context, markdown_chat, signals)
            )

            completion_task.add_done_callback(lambda t: receive_interrupt_task.cancel("Completion Task Finished"))

            await asyncio.wait(
                [receive_interrupt_task, completion_task],
                return_when=asyncio.ALL_COMPLETED
            )
            logger.info(f"AWAIT Await finished")

    except asyncio.CancelledError:
        logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
        await signals.control.kill.send_async(None)
        if receive_interrupt_task:
            receive_interrupt_task.cancel("Request cancelled due to client disconnection")
        if completion_task:
            completion_task.cancel("Request cancelled due to client disconnection")
    except Exception as e:
        logger.exception(e)
        await signals.output.error.send_async({"error": str(e)})
    finally:
        if receive_interrupt_task:
            receive_interrupt_task.cancel()
        if completion_task:
            completion_task.cancel()
        logger.info("DONE Closing websocket connection")

@completions_bp.after_websocket
async def cleanup(response: Response):
    logger.info(f'Request Finished.')
