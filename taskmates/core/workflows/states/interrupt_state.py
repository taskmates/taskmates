from typing import Optional


class InterruptState:
    """Holds the interrupt state for a transaction."""
    
    def __init__(self):
        self._state: Optional[str] = None  # None, "interrupting", "interrupted", "killed"
    
    @property
    def value(self) -> Optional[str]:
        return self._state
    
    @value.setter
    def value(self, state: Optional[str]):
        self._state = state
    
    def is_terminated(self) -> bool:
        """Check if the state indicates termination."""
        return self._state in ["interrupted", "killed"]
    
    def __repr__(self):
        return f"InterruptState({self._state})"


# Tests
def test_interrupt_state():
    state = InterruptState()
    
    # Initial state
    assert state.value is None
    assert not state.is_terminated()
    
    # Set to interrupting
    state.value = "interrupting"
    assert state.value == "interrupting"
    assert not state.is_terminated()
    
    # Set to interrupted
    state.value = "interrupted"
    assert state.value == "interrupted"
    assert state.is_terminated()
    
    # Set to killed
    state.value = "killed"
    assert state.value == "killed"
    assert state.is_terminated()
