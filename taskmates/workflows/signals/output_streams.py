import traceback

import pytest

from taskmates.workflow_engine.base_signals import BaseSignals
from taskmates.workflow_engine.signal_direction import SignalDirection


class OutputStreams(BaseSignals):
    signal_direction = SignalDirection.UPSTREAM

    def __init__(self):
        super().__init__()

        # TODO: Execution Context Outputs
        self.error = self.namespace.signal('error')
        self.result = self.namespace.signal('result')
        self.stdout = self.namespace.signal('stdout')

        self.artifact = self.namespace.signal('artifact')

        # TODO: Markdown Complete Job Outputs
        self.formatting = self.namespace.signal('response_formatting')
        self.responder = self.namespace.signal('responder')
        self.response = self.namespace.signal('response')
        self.next_responder = self.namespace.signal('next_responder')

        # TODO: Completion Task Outputs
        self.chat_completion = self.namespace.signal('chat_completion')
        self.code_cell_output = self.namespace.signal('code_cell_output')

        # Markdown Complete Job Bindings
        # TODO extract to a new Signals class
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
    output = OutputStreams()
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


@pytest.mark.asyncio
async def test_output_streams_copy():
    # Create original signals
    original = OutputStreams()

    # Create a copy
    copy = original.copy()

    # Verify they are different instances
    assert original is not copy
    assert original.namespace is not copy.namespace

    # Verify the signals are properly connected
    received_by_original = []
    received_by_copy = []

    @original.stdout.connect
    async def original_handler(sender):
        received_by_original.append(sender)

    @copy.stdout.connect
    async def copy_handler(sender):
        received_by_copy.append(sender)

    # Send a signal from the original
    await original.stdout.send_async('original')
    # In UPSTREAM mode, original signals should not propagate to copy
    assert received_by_original == ['original']
    assert received_by_copy == []

    # Send a signal from the copy
    await copy.stdout.send_async('copy')
    assert received_by_original == ['original', 'copy']
    assert received_by_copy == ['copy']
