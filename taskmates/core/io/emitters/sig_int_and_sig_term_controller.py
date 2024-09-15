import asyncio
import signal

from taskmates.core.processor import Processor
from taskmates.core.execution_environment import EXECUTION_ENVIRONMENT


class SigIntAndSigTermController(Processor):
    def __init__(self):
        self.received_signal = None
        self.task = None

    def __enter__(self):
        signal.signal(signal.SIGINT, self.handle)
        signal.signal(signal.SIGTERM, self.handle)
        self.task = asyncio.create_task(self.run_loop())

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.task.cancel()

    def handle(self, sig, frame):
        self.received_signal = sig

    async def run_loop(self):
        signals = EXECUTION_ENVIRONMENT.get().signals
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
