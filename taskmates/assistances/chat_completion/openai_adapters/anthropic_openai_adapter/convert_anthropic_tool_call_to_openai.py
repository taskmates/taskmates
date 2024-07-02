import json

from anthropic.types.beta.tools import ToolUseBlock
from typeguard import typechecked


@typechecked
def convert_anthropic_tool_call_to_openai(tool_call: ToolUseBlock):
    return {
        "index": 0,
        "id": f"call_{tool_call.id}",
        "function": {
            "arguments": json.dumps(tool_call.input, ensure_ascii=False),
            "name": tool_call.name
        }
    }
