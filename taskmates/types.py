import time
from pathlib import Path
from typing import MutableMapping, Dict, Any

from typeguard import typechecked
from typing_extensions import TypedDict, NotRequired, Literal


class Chat(TypedDict):
    markdown_chat: str
    run_opts: 'RunOpts'
    messages: list[dict]
    participants: dict
    available_tools: list[str]


class ApiRequest(TypedDict):
    type: str
    version: NotRequired[str]
    markdown_chat: str
    runner_environment: 'RunnerEnvironment'
    run_opts: 'RunOpts'


from typing import Union

class RunOpts(TypedDict):
    model: NotRequired[Union[str, dict]]
    workflow: NotRequired[str]
    tools: NotRequired[dict]
    participants: NotRequired[dict]

    max_steps: NotRequired[int]
    jupyter_enabled: NotRequired[bool]


class RunnerConfig(TypedDict):
    endpoint: NotRequired[str]
    interactive: NotRequired[bool]
    format: NotRequired[Literal["full", "text", "input", "completion"]]
    output: NotRequired[str]
    taskmates_dirs: NotRequired[list[str | Path]]


class RunnerEnvironment(TypedDict):
    request_id: NotRequired[str]
    markdown_path: NotRequired[str]
    cwd: NotRequired[str]
    env: NotRequired[MutableMapping[str, str]]


# TODO: move out

class StepContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]
    # TODO: move this to inputs
    current_step: NotRequired[int]


class JobContext(TypedDict):
    # TODO: move this to outputs
    markdown_chat: NotRequired[str]


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
