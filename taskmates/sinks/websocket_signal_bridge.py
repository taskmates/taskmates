import asyncio
import json
from typing import Optional, Dict, Any

import websockets
from loguru import logger
from pydantic import BaseModel, Field

import taskmates
from taskmates.config import CompletionContext, CompletionOpts
from taskmates.signals import Signals
from taskmates.sinks.streaming_sink import StreamingSink


class WebsocketSignalBridge(BaseModel, StreamingSink):
    websocket: Optional[websockets.WebSocketClientProtocol] = None
    signals: Optional[Signals] = None
    endpoint: str
    completion_context: CompletionContext
    completion_opts: CompletionOpts
    markdown_chat: str
    is_connected: bool = Field(default=False)

    class Config:
        arbitrary_types_allowed = True

    async def connect(self, signals: Signals):
        self.signals = signals
        try:
            self.websocket = await websockets.connect(self.endpoint)
            logger.info(f"Connected to WebSocket at {self.endpoint}")
            self.is_connected = True

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
        if not self.is_connected:
            logger.warning(f"WebSocket is not connected. Unable to send signal: {signal_name}")
            return

        message = self._prepare_message(signal_name, data)

        try:
            await self.websocket.send(message)
            logger.debug(f"Sent signal: {signal_name}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed. Unable to send signal.")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Failed to send signal {signal_name}: {e}")

    def _prepare_message(self, signal_name: str, data: Dict[str, Any] = None) -> str:
        if signal_name == "error":
            payload = {
                "type": signal_name,
                "payload": {
                    "error": str(data["error"]),
                }
            }
        elif signal_name in ["interrupt_request", "kill"]:
            payload = {
                "type": signal_name
            }
        elif signal_name == "completion":
            payload = {
                "type": "completion",
                "payload": {
                    "markdown_chunk": data
                }
            }
        else:
            raise ValueError(f"Unknown signal: {signal_name}")

        return json.dumps(payload, ensure_ascii=False)

    async def receive_messages(self):
        while self.is_connected:
            try:
                message = await self.websocket.recv()
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
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Error in receive_messages: {e}")
                self.is_connected = False
                break

    async def close(self):
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket connection closed")
