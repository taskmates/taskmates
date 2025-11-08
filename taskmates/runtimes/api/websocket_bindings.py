import asyncio
import functools
import traceback
from contextlib import asynccontextmanager

from loguru import logger
from quart import Websocket
from typeguard import typechecked

from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager
from taskmates.runtimes.api.background_task import background_task
from taskmates.runtimes.api.signals.web_socket_completion_streamer import WebSocketCompletionStreamer
from taskmates.runtimes.api.signals.web_socket_interrupt_and_kill_controller import \
    WebSocketInterruptAndKillController


@typechecked
class WebsocketBindings:
    def __init__(self, transaction: Transaction, websocket: Websocket):
        self.transaction = transaction
        self.websocket = websocket
        self._transaction_context = None

    async def __aenter__(self):
        # Set websocket resource
        self.transaction.resources["websocket"] = self.websocket

        # Enter transaction context first
        self._transaction_context = self.transaction.async_transaction_context()
        await self._transaction_context.__aenter__()

        # Set up daemons that bind transaction signals to websocket
        daemons = [
            ensure_async_context_manager(self._create_websocket_interrupt_and_kill_controller_background_task()),
            ensure_async_context_manager(self._create_websocket_completion_streamer_bindings()),
            ensure_async_context_manager(self._create_status_bindings()),
            self._create_exception_handler(),
        ]

        # Add daemons to transaction's async exit stack
        for daemon in daemons:
            await self.transaction.async_exit_stack.enter_async_context(daemon)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Exit transaction context (which handles daemon cleanup via exit stack)
        if self._transaction_context:
            return await self._transaction_context.__aexit__(exc_type, exc_val, exc_tb)

    def _create_websocket_completion_streamer_bindings(self):
        return self.transaction.consumes["execution_environment"].response.connected_to(
            WebSocketCompletionStreamer(websocket=self.websocket).handle_completion)

    def _create_status_bindings(self):
        async def noop(value):
            pass

        return stacked_contexts((self.transaction.consumes["status"].interrupted.connected_to(noop),
                                 self.transaction.consumes["status"].killed.connected_to(noop)))

    def _create_websocket_interrupt_and_kill_controller_background_task(self):
        controller = WebSocketInterruptAndKillController(websocket=self.websocket)
        control_signals = self.transaction.emits["control"]
        return background_task(lambda: controller.loop(control_signals))

    @asynccontextmanager
    async def _create_exception_handler(self):
        try:
            yield
        except asyncio.CancelledError:
            await self._handle_cancelled_error()
            raise
        except Exception as e:
            await self._handle_exception(e)
            raise
        finally:
            logger.info("DONE Closing websocket connection")

    async def _handle_exception(self, e):
        logger.exception(e)
        await self._handle_error(e, self.transaction.consumes["execution_environment"])

    async def _handle_cancelled_error(self):
        logger.info("REQUEST CANCELLED Request cancelled due to client disconnection")
        await self.transaction.emits["control"].kill.send_async({})

    async def _handle_error(self, error: Exception, execution_environment: ExecutionEnvironmentSignals):
        formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
        await execution_environment.response.send_async(sender="error", value=formatted)
