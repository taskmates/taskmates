import asyncio
import json

from loguru import logger
from quart import Websocket

from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.lib.json_.json_utils import snake_case


class WebSocketInterruptAndKillController:
    def __init__(self, websocket: Websocket):
        self.websocket = websocket

    async def loop(self, control_signals: ControlSignals):
        while True:
            try:
                raw_payload = await self.websocket.receive()
                payload = snake_case(json.loads(raw_payload))
                if payload.get("type") == "interrupt":
                    logger.info("Interrupt received")
                    await control_signals.send_interrupt({})
                elif payload.get("type") == "kill":
                    logger.info("Kill received")
                    await control_signals.send_kill({})
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                raise e
                # logger.error(f"Error processing WebSocket message: {e}")
                # break
            await asyncio.sleep(0.1)
