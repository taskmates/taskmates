import traceback

import pytest

from taskmates.core.signals.base_signals import BaseSignals


class ResponseSignals(BaseSignals):
    def __init__(self):
        super().__init__()

        # TODO: Chat Signals
        self.formatting = self.namespace.signal('response_formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.next_responder = self.namespace.signal('next_responder')

        # TODO: Task Signals
        self.chat_completion = self.namespace.signal('chat_completion')
        self.code_cell_output = self.namespace.signal('code_cell_output')

        # TODO: Response Stream signals
        self.error = self.namespace.signal('error')
        self.result = self.namespace.signal('result')
        self.stdout = self.namespace.signal('stdout')

        # TODO extract to a new Signals class
        # Derived/Bindings
        self.formatting.connect(self.stdout.send_async, weak=False)

        # TODO split below
        self.responder.connect(self.stdout.send_async, weak=False)
        self.response.connect(self.stdout.send_async, weak=False)
        self.next_responder.connect(self.stdout.send_async, weak=False)

        async def send_error_completion(error):
            formatted = f"**error>** {str(error)}: {type(error).__name__}\n\n<pre>\n{traceback.format_exc()}\n</pre>\n"
            await self.stdout.send_async(formatted)

        self.error.connect(send_error_completion, weak=False)


@pytest.mark.asyncio
async def test_error_completion():
    output = ResponseSignals()
    received = []

    @output.stdout.connect
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
