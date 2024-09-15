import json

from loguru import logger
from websockets import connect


class OutputSignalsToWebsocketBridge:
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
