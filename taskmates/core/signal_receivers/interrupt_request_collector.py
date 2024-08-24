from taskmates.core.signal_receiver import SignalReceiver
from taskmates.logging import logger
from taskmates.signals.signals import SIGNALS


class InterruptRequestCollector(SignalReceiver):
    def __init__(self):
        self.interrupt_requested = False

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            await SIGNALS.get().control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            await SIGNALS.get().control.interrupt.send_async({})
            self.interrupt_requested = True

    def connect(self, signals):
        signals.control.interrupt_request.connect(self.handle_interrupt_request)

    def disconnect(self, signals):
        signals.control.interrupt_request.disconnect(self.handle_interrupt_request)
