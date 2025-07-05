from typing import TypeVar, Generic, Callable, Any

import blinker

TSignal = TypeVar('TSignal', bound=dict)


class Signal(Generic[TSignal]):
    def __init__(self):
        self._signal = blinker.Signal()

    def connect(self, func: Callable[[Any, TSignal], None]):
        self._signal.connect(func)

    async def send_async(self, sender: Any, payload: TSignal):
        await self._signal.send_async(sender, **payload)
