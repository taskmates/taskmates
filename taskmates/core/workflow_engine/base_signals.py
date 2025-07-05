import asyncio
from contextlib import contextmanager
from typing import List, Tuple, TypeAlias, Sequence

import pytest
from blinker import Namespace

SourceTarget: TypeAlias = Tuple['BaseSignals', 'BaseSignals']


def relay(source_targets: Sequence[SourceTarget]):
    connected_handlers = []
    for from_signals, to_signals in source_targets:
        for name, signal in from_signals.namespace.items():
            source = from_signals.namespace[name]
            target = to_signals.namespace[name]
            receiver = source.connect(target.send_async, weak=False)
            connected_handlers.append((source, receiver))
    return connected_handlers


def disconnect_relay(handlers):
    for signal, handler in handlers:
        signal.disconnect(handler)


@contextmanager
def connected_signals(signal_pairs: List[SourceTarget]):
    handlers = relay(signal_pairs)
    try:
        yield
    finally:
        disconnect_relay(handlers)


class BaseSignals:
    def __init__(self):
        self.namespace = Namespace()

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()


# Tests
class TestSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.message_received = self.namespace.signal('message_received')
        self.message_processed = self.namespace.signal('message_processed')
        self.received_messages = []
        self.processed_messages = []

        async def on_message_received(sender, **kw):
            self.received_messages.append(kw['message'])

        async def on_message_processed(sender, **kw):
            self.processed_messages.append(kw['message'])

        self.message_received.connect(on_message_received, weak=False)
        self.message_processed.connect(on_message_processed, weak=False)


@pytest.mark.asyncio
async def test_signal_relay():
    signals1 = TestSignals()
    signals2 = TestSignals()
    signals3 = TestSignals()

    signal_pairs = [(signals1, signals2), (signals1, signals3)]

    with connected_signals(signal_pairs):
        await signals1.message_received.send_async(signals1, message='test message')
        # Give the event loop a chance to process all signals
        await asyncio.sleep(0)

        assert signals1.received_messages == ['test message']
        assert signals2.received_messages == ['test message']
        assert signals3.received_messages == ['test message']

    await signals1.message_received.send_async(signals1, message='after disconnect')
    await asyncio.sleep(0)

    assert signals1.received_messages == ['test message', 'after disconnect']
    assert signals2.received_messages == ['test message']
    assert signals3.received_messages == ['test message']


@pytest.mark.asyncio
async def test_multiple_signals():
    signals1 = TestSignals()
    signals2 = TestSignals()

    signal_pairs = [(signals1, signals2)]

    with connected_signals(signal_pairs):
        await signals1.message_received.send_async(signals1, message='received')
        await signals1.message_processed.send_async(signals1, message='processed')
        await asyncio.sleep(0)

        assert signals1.received_messages == ['received']
        assert signals1.processed_messages == ['processed']
        assert signals2.received_messages == ['received']
        assert signals2.processed_messages == ['processed']
