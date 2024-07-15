import asyncio
import json
from typing import Optional, Dict, Any

import websockets
from loguru import logger
from pydantic import BaseModel, Field

import taskmates
from taskmates.signals import Signals
from taskmates.sinks.streaming_sink import StreamingSink
from taskmates.config import CompletionContext, CompletionOpts


class WebsocketSignalBridge(BaseModel, StreamingSink):
    websocket: Optional[websockets.WebSocketClientProtocol] = None
    signals: Optional[Signals] = None
    endpoint: str
    completion_context: CompletionContext
    completion_opts: CompletionOpts
    markdown_chat: str

    class Config:
        arbitrary_types_allowed = True

    async def connect(self, signals: Signals):
        self.signals = signals
        try:
            self.websocket = await websockets.connect(self.endpoint)
            logger.info(f"Connected to WebSocket at {self.endpoint}")

            # Send initial payload
            initial_payload = {
                "version": taskmates.__version__,
                "completion_context": self.completion_context,
                "completion_opts": self.completion_opts,
                "markdown_chat": self.markdown_chat
            }
            await self.websocket.send(json.dumps(initial_payload))

            # Connect all relevant signals
            for signal_name, signal in signals.namespace.items():
                signal.connect(self.send_signal, weak=False)

            # Start listening for incoming messages
            asyncio.create_task(self.receive_messages())

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise
        return self

    async def send_signal(self, signal_name: str, data: Dict[str, Any] = None):
        if self.websocket is None:
            logger.warning("WebSocket is not connected")
            return

        if signal_name == "error":
            message = json.dumps({
                "type": "error",
                "payload": {
                    "error": str(data["error"]),
                }
            }, ensure_ascii=False)
        elif signal_name in ["interrupt_request", "kill"]:
            message = json.dumps({
                "type": signal_name
            }, ensure_ascii=False)
        else:
            message = json.dumps({
                "type": "completion",
                "payload": {
                    "markdown_chunk": data
                }
            }, ensure_ascii=False)

        try:
            await self.websocket.send(message)
            logger.debug(f"Sent signal: {signal_name}")
        except Exception as e:
            logger.error(f"Failed to send signal {signal_name}: {e}")

    async def receive_messages(self):
        if self.websocket is None:
            logger.warning("WebSocket is not connected")
            return

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if data["type"] in ["interrupt", "kill"]:
                        signal_name = f"{data['type']}_request"
                        if signal_name in self.signals.namespace:
                            await self.signals.namespace[signal_name].send_async(None)
                            logger.debug(f"Received and processed signal: {signal_name}")
                        else:
                            logger.warning(f"Received unknown signal: {signal_name}")
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON message")
                except KeyError:
                    logger.error("Received message with invalid format")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in receive_messages: {e}")

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")


# For backwards compatibility
WebsocketStreamingSink = WebsocketSignalBridge
