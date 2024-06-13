import re
from typing import Dict

from taskmates.signals import Signals


def snake_case_to_title_case(text: str) -> str:
    return re.sub(r'_([a-z])', lambda x: x.group(1).upper(), text.replace('_', ' ')).title()


class ChatCompletionEditorCompletion:
    def __init__(self, chat, signals: Signals):
        self.chat = chat
        self.signals = signals
        self.recipient = None
        self.role = None
        self.name = None

    async def process_chat_completion_chunk(self, choice: dict):
        delta = choice.get("delta", {})

        # role
        await self.on_received_role(delta)

        # text
        await self.on_received_content(choice)

        # tool calls
        await self.on_received_tool_calls(delta, choice)

    async def on_received_tool_calls(self, delta: Dict, choice: dict):
        # append tool calls
        tool_calls = delta.get("tool_calls", [])
        if tool_calls:
            for tool_call_json in tool_calls:
                await self.append_tool_calls(tool_call_json)

        # wrap up tool calls
        if choice.get("finish_reason", "") == "tool_calls":
            await self.append("`\n\n")

    async def append_tool_calls(self, tool_call_json: Dict):
        function = tool_call_json.get("function", {})
        if tool_call_json.get("id") is not None:
            index = tool_call_json.get("index", 0)
            code_cell_id = index + 1

            if index == 0:
                await self.append("\n\n###### Steps\n\n")
            else:
                await self.append("`\n")

            function_name = function.get("name", "")
            function_title = snake_case_to_title_case(function_name)
            tool_call_completion = f"- {function_title} [{code_cell_id}] `"
            await self.append(tool_call_completion)

        await self.append(function.get("arguments", ""))

    async def on_received_content(self, choice: dict):
        if choice["delta"].get("content"):
            await self.append(choice["delta"]["content"])

    async def on_received_role(self, delta: Dict):
        if not self.role and delta.get("role"):
            self.role = delta['role']
            recipient = self.chat["messages"][-1]["recipient"]
            await self.signals.responder.send_async(f"**{recipient}** ")

    async def append(self, text: str):
        await self.signals.response.send_async(text)
