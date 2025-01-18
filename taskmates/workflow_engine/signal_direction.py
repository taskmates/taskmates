from enum import Enum, auto

class SignalDirection(Enum):
    """Direction of signal flow when signals are copied/forked"""
    DOWNSTREAM = auto()  # Original -> Copy (e.g., control signals)
    UPSTREAM = auto()    # Copy -> Original (e.g., output signals)
