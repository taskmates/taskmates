import os
from typing import Dict

from taskmates.actions.invoke_function import invoke_function
from taskmates.assistances.completion_assistance import CompletionAssistance
from taskmates.assistances.markdown.tool_editor_completion import ToolEditorCompletion
from taskmates.config import CompletionContext
from taskmates.model.tool_call import ToolCall
from taskmates.signals import Signals
from taskmates.tools.function_registry import function_registry
from typeguard import typechecked

from taskmates.types import Chat


class MarkdownToolsAssistance(CompletionAssistance):
    def stop(self):
        raise NotImplementedError("Not implemented")

    def can_complete(self, chat: Dict) -> bool:
        messages = chat.get("messages", [])
        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", [])
        return len(tool_calls) > 0

    async def perform_completion(self, context: CompletionContext, chat: Chat, signals: Signals):
        cwd = context["cwd"]
        markdown_path = context["markdown_path"]

        messages = chat.get("messages", [])

        tool_calls = messages[-1].get("tool_calls", [])

        editor_completion = ToolEditorCompletion(project_dir=cwd, chat_file=markdown_path)

        for tool_call in tool_calls:
            function_title = tool_call["function"]["name"].replace("_", " ").title()
            await editor_completion.append_tool_execution_header(function_title, tool_call["id"], signals)

            tool_call_obj = ToolCall.from_dict(tool_call)

            async def handle_interrupted(sender):
                await signals.response.send_async("--- INTERRUPTED ---")

            with signals.interrupted.connected_to(handle_interrupted):
                original_cwd = os.getcwd()
                try:
                    os.chdir(cwd)
                    return_value = await self.execute_task(context, tool_call_obj, signals)
                finally:
                    os.chdir(original_cwd)

            await signals.response.send_async(str(return_value))
            await editor_completion.append_tool_execution_footer(function_title, signals)

    @staticmethod
    @typechecked
    async def execute_task(context: Dict, tool_call: ToolCall, signals):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments

        child_context = {**context, "tool_call_id": tool_call_id}

        function = function_registry[function_name]
        return_value = await invoke_function(function, arguments, signals)

        return return_value
