import asyncio
from contextlib import contextmanager
from typing import List, Tuple, TypeAlias, Sequence, Self, Any, Callable, Coroutine

import pytest
from blinker import NamedSignal

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


class TypedSignal(NamedSignal):
    def __init__(self, namespace: 'TypedNamespace', name: str, doc: str | None = None) -> None:
        super().__init__(doc)

        self.namespace = namespace
        self.name: str = name

    def __repr__(self) -> str:
        base = super().__repr__()
        return f"{base[:-1]}; {self.namespace.name}/{self.name!r}>"  # noqa: E702

    async def send_async(
            self,
            sender: Any | None = None,
            _sync_wrapper: Callable[
                               [Callable[..., Any]], Callable[..., Coroutine[Any, Any, Any]]
                           ]
                           | None = None,
            **kwargs: Any,
    ) -> list[tuple[Callable[..., Any], Any]]:
        # TODO: check for current transaction?
        # transaction = TRANSACTION.get()
        # transaction.execution_context

        if not self.receivers:
            raise ValueError(f"receivers not set: {self.namespace.name}/{self.name}")

        # print(f"Send async called: {self.namespace.name}/{self.name}")
        # ic(self, self.receivers)

        return await super().send_async(sender, **kwargs)


class TypedNamespace(dict[str, TypedSignal]):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name

    def signal(self, name: str, doc: str | None = None) -> TypedSignal:
        """Return the :class:`TypedSignal` for the given ``name``, creating it
        if required. Repeated calls with the same name return the same signal.

        :param name: The name of the signal.
        :param doc: The docstring of the signal.
        """
        if name not in self:
            self[name] = TypedSignal(self, name, doc)

        return self[name]


class BaseSignals:
    def __init__(self, name: str):
        self.namespace = TypedNamespace(name=name)

    def __del__(self):
        for name, signal in self.namespace.items():
            signal.receivers.clear()

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.namespace.name})"

    @contextmanager
    def connected_to(self: Self, other: Self):
        yield from connected_signals([self, other])


# Tests
class TestSignals(BaseSignals):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
    signals1 = TestSignals(name="signals1")
    signals2 = TestSignals(name="signals2")
    signals3 = TestSignals(name="signals3")

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
    signals1 = TestSignals(name="signals1")
    signals2 = TestSignals(name="signals2")

    signal_pairs = [(signals1, signals2)]

    with connected_signals(signal_pairs):
        await signals1.message_received.send_async(signals1, message='received')
        await signals1.message_processed.send_async(signals1, message='processed')
        await asyncio.sleep(0)

        assert signals1.received_messages == ['received']
        assert signals1.processed_messages == ['processed']
        assert signals2.received_messages == ['received']
        assert signals2.processed_messages == ['processed']
