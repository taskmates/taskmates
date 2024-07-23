import asyncio
import json

from loguru import logger

from taskmates.cli.lib.handler import Handler
from taskmates.lib.json_.json_utils import snake_case
from taskmates.signals.signals import Signals


class WebSocketInterruptAndKillHandler(Handler):
    def __init__(self, websocket):
        self.websocket = websocket
        self.task = None

    async def handle_interrupt_or_kill(self, signals: Signals):
        while True:
            try:
                raw_payload = await self.websocket.receive()
                payload = snake_case(json.loads(raw_payload))
                if payload.get("type") == "interrupt":
                    logger.info("Interrupt received")
                    await signals.control.interrupt_request.send_async(None)
                elif payload.get("type") == "kill":
                    logger.info("Kill received")
                    await signals.control.kill.send_async(None)
            except asyncio.CancelledError:
                break

    def connect(self, signals: Signals):
        self.task = asyncio.create_task(self.handle_interrupt_or_kill(signals))

    def disconnect(self, signals: Signals):
        if self.task and not self.task.done():
            self.task.cancel()
