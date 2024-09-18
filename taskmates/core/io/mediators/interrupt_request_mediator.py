from taskmates.core.processor import Processor
from taskmates.logging import logger
from taskmates.core.execution_context import EXECUTION_CONTEXT


class InterruptRequestMediator(Processor):
    def __init__(self):
        self.interrupt_requested = False

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().signals.control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            # TODO: Send this to the correct Task Signal
            await EXECUTION_CONTEXT.get().signals.control.interrupt.send_async({})
            self.interrupt_requested = True

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.control.interrupt_request.connect(self.handle_interrupt_request, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.control.interrupt_request.disconnect(self.handle_interrupt_request)
