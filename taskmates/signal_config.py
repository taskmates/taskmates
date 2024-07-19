from enum import Enum

from pydantic import BaseModel


class SignalMethod(Enum):
    DEFAULT = "default"
    WEBSOCKET = "websocket"


class SignalConfig(BaseModel):
    input_method: SignalMethod = SignalMethod.DEFAULT
    output_method: SignalMethod = SignalMethod.DEFAULT
    websocket_url: str = "ws://localhost:8765"  # Default WebSocket URL


def get_signal_config() -> SignalConfig:
    # In a real-world scenario, this might load from a config file or environment variables
    return SignalConfig()
