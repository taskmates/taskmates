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


import pytest
from unittest.mock import AsyncMock, MagicMock
from taskmates.core.workflows.signals.control_signals import ControlSignals


async def test_controller_loop_starts_and_cancels_cleanly():
    """Test that the controller loop can be started and cancelled without warnings"""
    websocket = AsyncMock()
    websocket.receive = AsyncMock(side_effect=asyncio.CancelledError())
    
    controller = WebSocketInterruptAndKillController(websocket)
    control_signals = MagicMock(spec=ControlSignals)
    
    # The loop should handle CancelledError gracefully and exit without re-raising
    await controller.loop(control_signals)


async def test_controller_handles_interrupt_signal():
    """Test that the controller properly handles interrupt signals"""
    websocket = AsyncMock()
    control_signals = AsyncMock(spec=ControlSignals)
    
    # Simulate receiving an interrupt message, then cancel
    async def mock_receive():
        await asyncio.sleep(0.01)
        return json.dumps({"type": "interrupt"})
    
    websocket.receive = mock_receive
    
    controller = WebSocketInterruptAndKillController(websocket)
    
    # Run the loop in a task so we can cancel it
    task = asyncio.create_task(controller.loop(control_signals))
    await asyncio.sleep(0.05)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify interrupt was sent
    control_signals.send_interrupt.assert_called_once_with({})


async def test_controller_handles_kill_signal():
    """Test that the controller properly handles kill signals and exits loop"""
    websocket = AsyncMock()
    control_signals = AsyncMock(spec=ControlSignals)
    
    # Simulate receiving a kill message
    websocket.receive = AsyncMock(return_value=json.dumps({"type": "kill"}))
    
    controller = WebSocketInterruptAndKillController(websocket)
    
    # Loop should exit cleanly after kill
    await controller.loop(control_signals)
    
    # Verify kill was sent
    control_signals.send_kill.assert_called_once_with({})
