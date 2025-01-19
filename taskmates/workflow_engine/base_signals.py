import asyncio
import contextlib
import functools
from contextlib import contextmanager
from typing import Dict, List, Set, Tuple, TypeVar

from blinker import Namespace, Signal

from taskmates.workflow_engine.signal_direction import SignalDirection


def relay(self_signals, other_signals):
    for signal_group_name, signal_group in vars(other_signals).items():
        if isinstance(signal_group, BaseSignals):
            for signal_name, other_signal in signal_group.namespace.items():
                self_signal = self_signals.__getattribute__(signal_name)
                self_signal.connect(functools.partial(other_signal, signal_name), weak=False)


def disconnect_relay(self_signals, other_signals):
    for signal_group_name, signal_group in vars(other_signals).items():
        if isinstance(signal_group, BaseSignals):
            for signal_name, other_signal in signal_group.namespace.items():
                self_signal = self_signals.__getattribute__(signal_name)
                self_signal.disconnect(other_signal)


@contextmanager
def connected_signals(this_signals: list['BaseSignals'], other_signals: list['BaseSignals']):
    relay(this_signals, other_signals)
    try:
        yield
    finally:
        disconnect_relay(this_signals, other_signals)


T = TypeVar('T', bound='BaseSignals')


class SignalRelay:
    _active_paths: Set[Tuple[int, int]] = set()  # Keep track of active signal paths to prevent recursion

    def __init__(self, source_signal: Signal, target_signal: Signal):
        self.source_signal = source_signal
        self.target_signal = target_signal
        self.handler = None

    def connect(self):
        @self.source_signal.connect
        async def relay_handler(sender, **kwargs):
            # Create a unique identifier for this signal path
            signal_path = (id(self.source_signal), id(self.target_signal))
            reverse_path = (id(self.target_signal), id(self.source_signal))

            # If either path is active, don't relay to avoid recursion
            if signal_path in self._active_paths or reverse_path in self._active_paths:
                return

            # Mark this path as being processed
            self._active_paths.add(signal_path)
            try:
                await self.target_signal.send_async(sender, **kwargs)
            finally:
                # Remove the path from active processing
                self._active_paths.remove(signal_path)

        self.handler = relay_handler

    def disconnect(self):
        if self.handler:
            self.source_signal.disconnect(self.handler)
            self.handler = None


def fork_signals(signals: Dict[str, T]) -> Dict[str, T]:
    """
    Creates a deep copy of a dictionary of signals and connects them to the original signals.

    Args:
        signals: A dictionary of BaseSignals instances

    Returns:
        A new dictionary with copied signals that are connected to the original signals
    """
    forked = {}
    for name, signal_group in signals.items():
        if isinstance(signal_group, BaseSignals):
            forked[name] = signal_group.copy()
    return forked


class BaseSignals:
    signal_direction = SignalDirection.DOWNSTREAM  # Default direction

    def __init__(self):
        self.namespace = Namespace()
        self._relays = []

    def __del__(self):
        # Clear signal receivers on GC
        for name, signal in self.namespace.items():
            signal.receivers.clear()
        # Disconnect all relays
        for relay in self._relays:
            relay.disconnect()

    def copy(self: T) -> T:
        """
        Creates a deep copy of the signals and connects them according to the signal_direction.

        Returns:
            A new instance of the same type with copied signals that are connected to the original signals
        """
        copied = self.__class__()
        for name, signal in self.namespace.items():
            copied.namespace.signal(name)

            if self.signal_direction == SignalDirection.DOWNSTREAM:
                # Original -> Copy
                relay = SignalRelay(signal, copied.namespace[name])
                relay.connect()
                self._relays.append(relay)
            else:  # UPSTREAM
                # Copy -> Original
                relay = SignalRelay(copied.namespace[name], signal)
                relay.connect()
                copied._relays.append(relay)

        return copied

    @contextlib.contextmanager
    def connected_to(self, objs: List[Signal], handler: callable):
        try:
            for obj in objs:
                obj.connect(handler)
            yield self
        finally:
            for obj in objs:
                obj.disconnect(handler)

    def connect_all(self, signals: 'BaseSignals'):
        """
        Connects all signals from another BaseSignals instance to this one.
        When a signal in the other instance is sent, it will trigger the corresponding signal in this instance.

        Args:
            signals: The BaseSignals instance to connect to
        """
        for name, signal in signals.namespace.items():
            if name in self.namespace:
                relay = SignalRelay(signal, self.namespace[name])
                relay.connect()
                self._relays.append(relay)

    def disconnect_all(self, signals: 'BaseSignals'):
        for signal_group_name, signal_group in vars(signals).items():
            if isinstance(signal_group, BaseSignals):
                for signal_name, signal in signal_group.namespace.items():
                    signal.disconnect(self.__getattribute__(signal_name))


class TestSignals(BaseSignals):
    def __init__(self):
        super().__init__()
        self.namespace.signal('test_signal')

    @property
    def test_signal(self) -> Signal:
        return self.namespace['test_signal']


async def test_base_signals_copy():
    # Create original signals
    original = TestSignals()

    # Create a copy
    copy = original.copy()

    # Verify they are different instances
    assert original is not copy
    assert original.namespace is not copy.namespace

    # Verify the signals are properly connected
    received_by_original = []
    received_by_copy = []

    @original.test_signal.connect
    async def original_handler(sender):
        received_by_original.append(sender)

    @copy.test_signal.connect
    async def copy_handler(sender):
        received_by_copy.append(sender)

    # Send a signal from the original
    await original.test_signal.send_async('original')
    assert received_by_original == ['original']
    assert received_by_copy == ['original']

    # Send a signal from the copy
    await copy.test_signal.send_async('copy')
    # In DOWNSTREAM mode, copy signals should not propagate to original
    assert received_by_original == ['original']
    assert received_by_copy == ['original', 'copy']


async def test_base_signals_copy_upstream():
    # Create a signals class with upstream direction
    class UpstreamSignals(TestSignals):
        signal_direction = SignalDirection.UPSTREAM

    # Create original signals
    original = UpstreamSignals()

    # Create a copy
    copy = original.copy()

    # Verify they are different instances
    assert original is not copy
    assert original.namespace is not copy.namespace

    # Verify the signals are properly connected
    received_by_original = []
    received_by_copy = []

    @original.test_signal.connect
    async def original_handler(sender):
        received_by_original.append(sender)

    @copy.test_signal.connect
    async def copy_handler(sender):
        received_by_copy.append(sender)

    # Send a signal from the original
    await original.test_signal.send_async('original')
    # In UPSTREAM mode, original signals should not propagate to copy
    assert received_by_original == ['original']
    assert received_by_copy == []

    # Send a signal from the copy
    await copy.test_signal.send_async('copy')
    assert received_by_original == ['original', 'copy']
    assert received_by_copy == ['copy']


async def test_fork_signals():
    # Create a dictionary of signals
    original_signals = {
        'test_signals': TestSignals()
    }

    # Fork the signals
    forked_signals = fork_signals(original_signals)

    # Verify they are different instances
    assert original_signals is not forked_signals
    assert original_signals['test_signals'] is not forked_signals['test_signals']

    # Verify the signals are properly connected
    received_by_original = []
    received_by_fork = []

    @original_signals['test_signals'].test_signal.connect
    async def original_handler(sender):
        received_by_original.append(sender)

    @forked_signals['test_signals'].test_signal.connect
    async def fork_handler(sender):
        received_by_fork.append(sender)

    # Send a signal from the original
    await original_signals['test_signals'].test_signal.send_async('original')
    assert received_by_original == ['original']
    assert received_by_fork == ['original']

    # Send a signal from the fork
    await forked_signals['test_signals'].test_signal.send_async('fork')
    # In DOWNSTREAM mode, fork signals should not propagate to original
    assert received_by_original == ['original']
    assert received_by_fork == ['original', 'fork']
