import asyncio
import json

from loguru import logger
from websockets import connect

# NOTE: WIP
class WebsocketToControlSignalsBridge:
    def __init__(self, control_signals, websocket_url):
        self.control_signals = control_signals
        self.websocket_url = websocket_url
        self.websocket = None

    async def connect(self):
        self.websocket = await connect(self.websocket_url)
        logger.info(f"Connected to WebSocket at {self.websocket_url}")
        asyncio.create_task(self._receive_messages())

    async def _receive_messages(self):
        while True:
            try:
                message = await self.websocket.recv()
                await self._process_message(message)
            except Exception as e:
                logger.error(f"Error in receiving message: {e}")
                break

    async def _process_message(self, message):
        try:
            data = json.loads(message)
            signal_name = data.get('type')
            if signal_name in self.control_signals.namespace:
                await self.control_signals.namespace[signal_name].send_async(data.get('payload'))
                logger.debug(f"Processed control signal: {signal_name}")
            else:
                logger.warning(f"Received unknown signal: {signal_name}")
        except json.JSONDecodeError:
            logger.error("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")
