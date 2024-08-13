from taskmates.core.handlers.handler import Handler
from taskmates.logging import logger

class InterruptRequestHandler(Handler):
    def __init__(self, signals):
        self.interrupt_requested = False
        self.signals = signals

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            await self.signals.control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            await self.signals.control.interrupt.send_async({})
            self.interrupt_requested = True

    def connect(self, signals):
        signals.control.interrupt_request.connect(self.handle_interrupt_request)

    def disconnect(self, signals):
        signals.control.interrupt_request.disconnect(self.handle_interrupt_request)
