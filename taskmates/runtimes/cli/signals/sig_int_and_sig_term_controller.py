import asyncio
import signal

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflows.signals.control_signals import ControlSignals


class SigIntAndSigTermController(CompositeContextManager):
    def __init__(self, control_signals: ControlSignals):
        super().__init__()
        self.control_signals = control_signals
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
        while True:
            if self.received_signal == signal.SIGINT:
                print(flush=True)
                print("Interrupting...", flush=True)
                print("Press Ctrl+C again to kill", flush=True)
                await self.control_signals.interrupt_request.send_async({})
                # await asyncio.sleep(5)
                self.received_signal = None
            elif self.received_signal == signal.SIGTERM:
                await self.control_signals.kill.send_async({})
                # await asyncio.sleep(5)
                break
            await asyncio.sleep(0.1)
