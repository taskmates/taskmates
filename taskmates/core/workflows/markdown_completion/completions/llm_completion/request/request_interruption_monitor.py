from dataclasses import dataclass, field
from typing import Any

import pytest
from typeguard import typechecked

from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals


# TODO rename this class
@typechecked
@dataclass
class RequestInterruptionMonitor:
    """
    A class that manages the interrupt/kill logic for a request.
    """
    status: StatusSignals
    control: ControlSignals
    response: Any = field(default=None)
    interrupted_or_killed: bool = field(default=False)

    async def interrupt_handler(self, sender):
        """Handle interrupt signal"""
        self.interrupted_or_killed = True
        if self.response:
            await self.response.aclose()
        await self.status.interrupted.send_async(None)

    async def kill_handler(self, sender):
        """Handle kill signal"""
        self.interrupted_or_killed = True
        if self.response:
            await self.response.aclose()
        await self.status.killed.send_async(None)

    # TODO: this can probably be removed
    def set_response(self, response):
        """Set the response object"""
        self.response = response

    async def __aenter__(self):
        """Connect interrupt and kill handlers"""
        self.control.interrupt.connect(self.interrupt_handler)
        self.control.kill.connect(self.kill_handler)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect interrupt and kill handlers"""
        self.control.interrupt.disconnect(self.interrupt_handler)
        self.control.kill.disconnect(self.kill_handler)


@pytest.mark.asyncio
async def test_interruptible_request_interrupt():
    class MockSignal:
        async def send_async(self, value):
            pass

        def connect(self, handler):
            self.handler = handler

        def disconnect(self, handler):
            pass

    class MockStatus:
        def __init__(self):
            self.interrupted = MockSignal()
            self.killed = MockSignal()

    class MockControl:
        def __init__(self):
            self.interrupt = MockSignal()
            self.kill = MockSignal()

    class MockResponse:
        async def aclose(self):
            self.closed = True

    status = MockStatus()
    control = MockControl()
    response = MockResponse()

    request = RequestInterruptionMonitor(status=status, control=control)
    request.set_response(response)

    async with request:
        await control.interrupt.handler(None)
        assert request.interrupted_or_killed
        assert response.closed


@pytest.mark.asyncio
async def test_interruptible_request_kill():
    class MockSignal:
        async def send_async(self, value):
            pass

        def connect(self, handler):
            self.handler = handler

        def disconnect(self, handler):
            pass

    class MockStatus:
        def __init__(self):
            self.interrupted = MockSignal()
            self.killed = MockSignal()

    class MockControl:
        def __init__(self):
            self.interrupt = MockSignal()
            self.kill = MockSignal()

    class MockResponse:
        async def aclose(self):
            self.closed = True

    status = MockStatus()
    control = MockControl()
    response = MockResponse()

    request = RequestInterruptionMonitor(status=status, control=control)
    request.set_response(response)

    async with request:
        await control.kill.handler(None)
        assert request.interrupted_or_killed
        assert response.closed
