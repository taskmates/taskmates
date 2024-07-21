import contextvars
import traceback
from contextlib import contextmanager
from typing import List

import pytest
from blinker import Namespace


class Signals:
    def __init__(self):
        self.input = InputSignals()
        self.control = ControlSignals()
        self.lifecycle = LifecycleSignals()
        self.response = ResponseSignals()
        self.output = OutputSignals()

    @contextmanager
    def connected_to(self, objs: List):
        try:
            for obj in objs:
                obj.connect(self)
            yield
        finally:
            for obj in objs:
                obj.disconnect(self)


SIGNALS: contextvars.ContextVar['Signals'] = contextvars.ContextVar('signals')


class BaseSignals:
    def __init__(self):
        self.namespace = Namespace()

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()


class ControlSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.interrupt_request = self.namespace.signal('interrupt_request')
        self.interrupt = self.namespace.signal('interrupt')
        self.kill = self.namespace.signal('kill')


class InputSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.input = self.namespace.signal('input')


class OutputSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.artifact = self.namespace.signal('artifact')
        self.return_value = self.namespace.signal('return_value')


class LifecycleSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.start = self.namespace.signal('start')
        self.finish = self.namespace.signal('finish')
        self.success = self.namespace.signal('success')
        self.interrupted = self.namespace.signal('interrupted')
        self.killed = self.namespace.signal('killed')


class ResponseSignals(LifecycleSignals):
    def __init__(self):
        super().__init__()

        # Output
        self.formatting = self.namespace.signal('formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.next_responder = self.namespace.signal('next_responder')

        # Internal ouptut signals
        self.chat_completion = self.namespace.signal('chat_completion')
        self.code_cell_output = self.namespace.signal('code_cell_output')

        # Logging signals
        self.error = self.namespace.signal('error')

        # Completion signal
        self.completion = self.namespace.signal('completion')

        # Derived
        self.formatting.connect(self.completion.send_async, weak=False)
        self.responder.connect(self.completion.send_async, weak=False)
        self.response.connect(self.completion.send_async, weak=False)
        self.next_responder.connect(self.completion.send_async, weak=False)

        async def send_error_completion(error):
            formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
            await self.completion.send_async(formatted)

        self.error.connect(send_error_completion, weak=False)


@pytest.mark.asyncio
async def test_error_completion():
    output = ResponseSignals()
    received = []

    @output.completion.connect
    async def receiver(sender):
        received.append(sender)

    try:
        raise ValueError("Test error")
    except ValueError as e:
        await output.error.send_async(e)

    assert len(received) == 1
    assert "**error>** Test error: ValueError" in received[0]
    assert "<pre>" in received[0]
    assert "Traceback (most recent call last):" in received[0]
