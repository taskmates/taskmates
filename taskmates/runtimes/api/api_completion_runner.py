import asyncio
import traceback

from loguru import logger
from typeguard import typechecked

from taskmates.logging import file_logger
from taskmates.types import ApiRequest
from taskmates.core.workflow_engine.default_environment_signals import default_environment_signals
from taskmates.core.workflow_engine.environment import environment
from taskmates.core.workflow_engine.run import to_daemons_dict, RUN, Objective, ObjectiveKey
from taskmates.runtimes.api.api_context_builder import ApiContextBuilder
from taskmates.core.workflows.markdown_completion.markdown_complete import MarkdownComplete
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.runtimes.api.signals.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.runtimes.api.signals.web_socket_interrupt_and_kill_controller import \
    WebSocketInterruptAndKillController


class ApiCompletionRunner:
    def __init__(self, websocket):
        self.resources = {"websocket": websocket}

    @typechecked
    async def run(self, payload: ApiRequest):
        @environment(
            fulfillers={
                'objective': lambda: Objective(key=ObjectiveKey(outcome="api_completion")),
                'context': lambda: ApiContextBuilder(payload).build(),
                'daemons': lambda: to_daemons_dict([
                    WebSocketInterruptAndKillController(self.resources["websocket"]),
                    WebSocketCompletionStreamer(self.resources["websocket"])
                ]),
                'state': lambda: {},
                'results': lambda: {},
                'signals': lambda: default_environment_signals()
            })
        async def attempt_api_completion(payload):

            run = RUN.get()
            await run.signals["status"].start.send_async({})

            try:
                file_logger.debug("websockets_api_payload.json", content=payload)

                markdown_chat = payload["markdown_chat"]
                return await MarkdownComplete().fulfill(markdown_chat=markdown_chat)

            # TODO: remove after we properly tested client disconnect
            except asyncio.CancelledError:
                logger.info("REQUEST CANCELLED Request cancelled due to client disconnection")
                await run.signals["control"].kill.send_async({})
            except Exception as e:
                logger.exception(e)
                await self.handle_error(e, run.signals["execution_environment"])
            finally:
                logger.info("DONE Closing websocket connection")

        return await attempt_api_completion(payload)

    async def handle_error(self, error: Exception, execution_environment: ExecutionEnvironmentSignals):
        formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
        await execution_environment.stdout.send_async(formatted)
