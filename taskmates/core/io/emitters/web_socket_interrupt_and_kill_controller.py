import asyncio
import json

from loguru import logger

from taskmates.core.execution_context import EXECUTION_CONTEXT
from taskmates.core.processor import Processor
from taskmates.lib.json_.json_utils import snake_case


class WebSocketInterruptAndKillController(Processor):
    def __init__(self, websocket):
        self.websocket = websocket
        self.task = None

    async def run_loop(self, control):
        while True:
            try:
                raw_payload = await self.websocket.receive()
                payload = snake_case(json.loads(raw_payload))
                if payload.get("type") == "interrupt":
                    logger.info("Interrupt received")
                    await control.interrupt_request.send_async({})
                elif payload.get("type") == "kill":
                    logger.info("Kill received")
                    await control.kill.send_async({})
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                raise e
                # logger.error(f"Error processing WebSocket message: {e}")
                # break
            await asyncio.sleep(0.1)

    def __enter__(self):
        control = EXECUTION_CONTEXT.get().signals.control
        self.task = asyncio.create_task(self.run_loop(control))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.task and not self.task.done():
            self.task.cancel()
