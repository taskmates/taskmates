import json
import time
from typing import Dict, Any

from typeguard import typechecked

# TODO: move to types.py
@typechecked
class ToolCall:
    def __init__(self, id: str | None = None,
                 type: str = "function",
                 function: 'ToolCall.Function' = None,
                 # tool_call: Dict[str, Any] = None,
                 # name: str = None,
                 # arguments: Dict[str, Any] = None
                 ):
        if id is None:
            self.id: str = f"tool_call_{int(time.time() * 1000)}"
        else:
            self.id: str = id
        self.type: str = type
        self.function: 'ToolCall.Function' = function

        # if tool_call is not None:
        #     self.id = f"tool_call_{int(time.time() * 1000)}"
        #     function_data = tool_call.get("function", {})
        #     self.function = ToolCall.Function(function_data.get("name"), function_data.get("arguments"))
        #
        # if name is not None and arguments is not None:
        #     self.id = f"tool_call_{int(time.time() * 1000)}"
        #     self.function = ToolCall.Function(name, arguments)

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ToolCall':
        return ToolCall(
            id=data.get("id"),
            function=ToolCall.Function.from_dict(data.get("function")),
        )

    @typechecked
    class Function:
        def __init__(self, name: str, arguments: Dict[str, Any]):
            self.name: str = name
            self.arguments: dict = arguments

        def __getitem__(self, item):
            return getattr(self, item)

        @staticmethod
        def from_dict(data: Dict[str, Any]) -> 'ToolCall.Function':
            return ToolCall.Function(
                name=data.get("name"),
                arguments=data["arguments"],
            )
