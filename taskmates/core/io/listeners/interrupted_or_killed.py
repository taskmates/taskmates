from taskmates.core.processor import Processor
from taskmates.core.execution_context import EXECUTION_CONTEXT


class InterruptedOrKilled(Processor):
    def __init__(self):
        self.interrupted_or_killed = False

    async def handle_interrupted(self, _sender):
        self.interrupted_or_killed = True

    async def handle_killed(self, _sender):
        self.interrupted_or_killed = True

    def __enter__(self):
        signals = EXECUTION_CONTEXT.get().signals
        signals.lifecycle.interrupted.connect(self.handle_interrupted, weak=False)
        signals.lifecycle.killed.connect(self.handle_killed, weak=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signals = EXECUTION_CONTEXT.get().signals
        signals.lifecycle.interrupted.disconnect(self.handle_interrupted)
        signals.lifecycle.killed.disconnect(self.handle_killed)
