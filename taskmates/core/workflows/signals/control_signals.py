from typing import TypedDict

from taskmates.core.workflow_engine.base_signals import BaseSignals


class InterruptRequestSignal(TypedDict):
    pass


class InterruptSignal(TypedDict):
    pass


class KillSignal(TypedDict):
    pass


class ControlSignals(BaseSignals):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interrupt_request = self.namespace.signal('interrupt_request')
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')

    async def send_interrupt_request(self, signal: InterruptRequestSignal):
        await self.interrupt_request.send_async(signal)

    async def send_interrupt(self, signal: InterruptSignal):
        await self.interrupt.send_async(signal)

    async def send_kill(self, signal: KillSignal):
        await self.kill.send_async(signal)
