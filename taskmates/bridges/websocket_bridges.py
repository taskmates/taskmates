import json
import asyncio
from websockets import connect, WebSocketClientProtocol
from loguru import logger

class SignalToWebsocketBridge:
    def __init__(self, output_signals, websocket_url):
        self.output_signals = output_signals
        self.websocket_url = websocket_url
        self.websocket = None

    async def connect(self):
        self.websocket = await connect(self.websocket_url)
        logger.info(f"Connected to WebSocket at {self.websocket_url}")
        self._connect_signals()

    def _connect_signals(self):
        for name, signal in self.output_signals.namespace.items():
            signal.connect(self._send_signal, weak=False)

    async def _send_signal(self, signal_name, data=None):
        if not self.websocket:
            logger.warning(f"WebSocket is not connected. Unable to send signal: {signal_name}")
            return

        message = self._prepare_message(signal_name, data)
        try:
            await self.websocket.send(message)
            logger.debug(f"Sent signal: {signal_name}")
        except Exception as e:
            logger.error(f"Failed to send signal {signal_name}: {e}")

    def _prepare_message(self, signal_name, data):
        payload = {
            "type": signal_name,
            "payload": data
        }
        return json.dumps(payload, ensure_ascii=False)

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")

class WebsocketToSignalBridge:
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
