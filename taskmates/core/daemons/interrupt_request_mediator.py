from loguru import logger

from taskmates.core.daemon import Daemon
from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.lib.contextlib_.stacked_contexts import stacked_contexts


class InterruptRequestMediator(Daemon):
    def __init__(self):
        super().__init__()
        self.interrupt_requested = False

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().control.interrupt.send_async({})
            self.interrupt_requested = True

    def __enter__(self):
        execution_context = EXECUTION_CONTEXT.get()
        self.exit_stack.enter_context(stacked_contexts([
            execution_context.control.interrupt_request.connected_to(self.handle_interrupt_request)
        ]))
