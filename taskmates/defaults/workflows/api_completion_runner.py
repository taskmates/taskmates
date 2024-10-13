import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.context_builders.api_context_builder import ApiContextBuilder
from taskmates.core.io.emitters.web_socket_interrupt_and_kill_controller import WebSocketInterruptAndKillController
from taskmates.core.io.listeners.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.core.run import Run, jobs_to_dict
from taskmates.defaults.workflows.markdown_complete import MarkdownComplete
from taskmates.types import ApiRequest


class ApiCompletionRunner:
    def __init__(self, websocket):
        self.resources = {"websocket": websocket}

    @typechecked
    async def run(self, payload: ApiRequest):
        contexts = ApiContextBuilder(payload).build()

        io = jobs_to_dict([
            WebSocketInterruptAndKillController(self.resources["websocket"]),
            WebSocketCompletionStreamer(self.resources["websocket"]),
        ])

        with Run(contexts=contexts, jobs=io) as run:
            try:
                await run.output_streams.artifact.send_async(
                    {"name": "websockets_api_payload.json", "content": payload})

                markdown_chat = payload["markdown_chat"]
                return await MarkdownComplete(contexts=contexts).run(markdown_chat=markdown_chat)

            # TODO: remove after we properly tested client disconnect
            except asyncio.CancelledError:
                logger.info(f"REQUEST CANCELLED Request cancelled due to client disconnection")
                await run.control.kill.send_async({})
            except Exception as e:
                await run.output_streams.error.send_async(e)
            finally:
                logger.info("DONE Closing websocket connection")
