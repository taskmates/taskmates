import asyncio
import signal

from taskmates.signals.handler import Handler
from taskmates.signals.signals import Signals


class SigIntAndSigTermController(Handler):
    def __init__(self):
        self.received_signal = None
        self.task = None

    def connect(self, signals: Signals):
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGTERM, self.handle)
        self.task = asyncio.create_task(self.emit_signals(signals))

    def disconnect(self, signals: Signals):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.task.cancel()

    def handle(self, sig, frame):
        self.received_signal = sig

    async def emit_signals(self, signals: Signals):
        while True:
            if self.received_signal == signal.SIGINT:
                print(flush=True)
                print("Interrupting...", flush=True)
                print("Press Ctrl+C again to kill", flush=True)
                await signals.control.interrupt_request.send_async({})
                await asyncio.sleep(5)
                self.received_signal = None
            elif self.received_signal == signal.SIGTERM:
                await signals.control.kill.send_async({})
                await asyncio.sleep(5)
                break
            await asyncio.sleep(0.1)
