import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.workflows.context_builders.api_context_builder import ApiContextBuilder
from taskmates.workflows.signals.sinks.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.run import to_daemons_dict
from taskmates.workflows.signals.sources.web_socket_interrupt_and_kill_controller import WebSocketInterruptAndKillController
from taskmates.workflows.markdown_complete import MarkdownComplete
from taskmates.types import ApiRequest


class ApiCompletionRunner:
    def __init__(self, websocket):
        self.resources = {"websocket": websocket}

    @typechecked
    async def run(self, payload: ApiRequest):
        context = ApiContextBuilder(payload).build()

        daemons = to_daemons_dict([
            WebSocketInterruptAndKillController(self.resources["websocket"]),
            WebSocketCompletionStreamer(self.resources["websocket"]),
        ])

        outcome = "api_completion"

        async def attempt_api_completion(outcome, context, daemons, payload):
            with Objective(outcome=outcome).attempt(context=context, daemons=daemons) as run:
                await run.signals["status"].start.send_async({})

                try:
                    await run.signals["output_streams"].artifact.send_async(
                        {"name": "websockets_api_payload.json", "content": payload})

                    markdown_chat = payload["markdown_chat"]
                    return await MarkdownComplete().fulfill(markdown_chat=markdown_chat)

                # TODO: remove after we properly tested client disconnect
                except asyncio.CancelledError:
                    logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
                    await run.signals["control"].kill.send_async({})
                # TODO: move this out
                except Exception as e:
                    await run.signals["output_streams"].error.send_async(e)
                finally:
                    logger.info("DONE Closing websocket connection")

        return await attempt_api_completion(outcome, context, daemons, payload)
