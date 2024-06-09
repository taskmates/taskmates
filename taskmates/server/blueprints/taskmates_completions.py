import asyncio
import json

from loguru import logger
from quart import Blueprint, Response
from quart import websocket

from taskmates.assistances.markdown.markdown_completion_assistance import MarkdownCompletionAssistance
from taskmates.config import CompletionContext, CompletionOpts, COMPLETION_CONTEXT, COMPLETION_OPTS, \
    updated_config
from taskmates.lib.json_.json_utils import snake_case
from taskmates.lib.logging_.file_logger import file_logger
from taskmates.signals import SIGNALS, Signals
from taskmates.sinks import WebsocketStreamingSink
from taskmates.types import CompletionPayload

completions_bp = Blueprint('completions_v2', __name__)


@completions_bp.websocket('/v2/taskmates/completions')
async def taskmates_completions():
    # response handlers
    signals = Signals()
    token = SIGNALS.set(signals)
    WebsocketStreamingSink().connect(signals)

    try:
        logger.info("Waiting for websocket connection at /v2/taskmates/completions")
        raw_payload = await websocket.receive()
        # print(f"raw_payload: {raw_payload}")

        payload: CompletionPayload = snake_case(json.loads(raw_payload))

        completion_context: CompletionContext = payload["completion_context"]
        completion_opts: CompletionOpts = payload["completion_opts"]
        request_id = completion_context['request_id']
        markdown_chat = payload["markdown_chat"]

        with file_logger.contextualize(request_id=(request_id)), \
                updated_config(COMPLETION_CONTEXT, completion_context), \
                updated_config(COMPLETION_OPTS, completion_opts):
            logger.info(f"[{request_id}] CONNECT /v2/taskmates/completions")

            file_logger.debug("request_payload.yaml", content=payload)

            async def handle_interrupt():
                try:
                    raw_payload = await websocket.receive()
                    payload = snake_case(json.loads(raw_payload))
                    if payload.get("type") == "interrupt":
                        logger.info(f"INTERRUPT Received interrupt message for request {request_id}")
                        await signals.interrupt.send_async(None)
                        return
                    elif payload.get("type") == "kill":
                        logger.info(f"KILL Received kill message for request {request_id}")
                        await signals.kill.send_async(None)
                        return
                except asyncio.CancelledError:
                    # logger.info(f"INTERRUPT TASK CANCELLED Interrupt task for request {request_id} was cancelled")
                    pass
                finally:
                    pass
                    # logger.info(f"Interrupt task for request {request_id} finished")

            receive_interrupt_task = asyncio.create_task(handle_interrupt())

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
        await signals.kill.send_async(None)
        receive_interrupt_task.cancel("Request cancelled due to client disconnection")
        completion_task.cancel("Request cancelled due to client disconnection")
    except Exception as e:
        logger.exception(e)
        await signals.error.send_async(e)

    print("DONE Closing websocket connection")
    # return Response("Done", status=200)


@completions_bp.after_websocket
async def cleanup(response: Response):
    # logger.info(f'Request Finished. {response.status}')
    logger.info(f'Request Finished.')
