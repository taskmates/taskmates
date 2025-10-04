import asyncio
import functools
import traceback
from contextlib import asynccontextmanager

from loguru import logger
from quart import Websocket
from typeguard import typechecked

from taskmates.core.workflow_engine.transaction import Transaction
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts, ensure_async_context_manager
from taskmates.runtimes.api.background_task import background_task
from taskmates.runtimes.api.signals.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.runtimes.api.signals.web_socket_interrupt_and_kill_controller import \
    WebSocketInterruptAndKillController


@typechecked
class ApiCompletionTransaction(Transaction):
    def __init__(self, websocket: Websocket, **kwargs):
        super().__init__(**kwargs)
        self.resources = {"websocket": websocket}

        # Create async context managers after parent initialization
        self.async_context_managers = [
            ensure_async_context_manager(self.create_websocket_interrupt_and_kill_controller_background_task()),
            ensure_async_context_manager(self.create_websocket_completion_streamer_bindings()),
            ensure_async_context_manager(self.create_status_bindings()),
            self.create_exception_handler(),
        ]

    # def context_managers(self):
    #     return stacked_contexts(
    #         self.create_websocket_interrupt_and_kill_controller_background_task(),
    #         self.create_websocket_completion_streamer_bindings(),
    #         self.create_status_bindings(),
    #     )

    async def handle_exception(self, e):
        logger.exception(e)
        await self.handle_error(e, self.consumes["execution_environment"])

    async def handle_cancelled_error(self):
        # TODO: remove after we properly tested client disconnect
        logger.info("REQUEST CANCELLED Request cancelled due to client disconnection")
        await self.emits["control"].kill.send_async({})

    def create_websocket_completion_streamer_bindings(self):
        return self.consumes["execution_environment"].response.connected_to(
            WebSocketCompletionStreamer(websocket=self.resources["websocket"]).handle_completion)

    def create_status_bindings(self):
        async def noop(value):
            pass

        return stacked_contexts((self.consumes["status"].interrupted.connected_to(noop),
                                 self.consumes["status"].killed.connected_to(noop)))

    def create_websocket_interrupt_and_kill_controller_background_task(self):
        return background_task(
            functools.partial(WebSocketInterruptAndKillController(
                websocket=self.resources["websocket"]).loop,
                              control_signals=self.execution_context.emits["control"]))

    @asynccontextmanager
    async def create_exception_handler(self):
        try:
            yield
        except asyncio.CancelledError:
            await self.handle_cancelled_error()
            raise
        except Exception as e:
            await self.handle_exception(e)
            raise
        finally:
            logger.info("DONE Closing websocket connection")

    async def handle_error(self, error: Exception, execution_environment: ExecutionEnvironmentSignals):
        formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
        await execution_environment.response.send_async(sender="error", value=formatted)
