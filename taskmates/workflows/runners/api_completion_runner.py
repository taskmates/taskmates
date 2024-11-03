import asyncio

from loguru import logger
from typeguard import typechecked

from taskmates.types import ApiRequest
from taskmates.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.workflow_engine.environment import environment
from taskmates.workflow_engine.objective import Objective
from taskmates.workflow_engine.run import to_daemons_dict, RUN
from taskmates.workflows.context_builders.api_context_builder import ApiContextBuilder
from taskmates.workflows.markdown_complete import MarkdownComplete
from taskmates.workflows.signals.sinks.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.workflows.signals.sources.web_socket_interrupt_and_kill_controller import \
    WebSocketInterruptAndKillController


class ApiCompletionRunner:
    def __init__(self, websocket):
        self.resources = {"websocket": websocket}

    @typechecked
    async def run(self, payload: ApiRequest):
        @environment(
            fulfillers={
                'objective': lambda: Objective(outcome="api_completion"),
                'context': lambda: ApiContextBuilder(payload).build(),
                'daemons': lambda: to_daemons_dict([
                    WebSocketInterruptAndKillController(self.resources["websocket"]),
                    WebSocketCompletionStreamer(self.resources["websocket"]),
                ]),
                'state': lambda: {},
                'results': lambda: {},
                'signals': lambda: default_environment_signals()
            })
        async def attempt_api_completion(payload):
            run = RUN.get()
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

        return await attempt_api_completion(payload)
