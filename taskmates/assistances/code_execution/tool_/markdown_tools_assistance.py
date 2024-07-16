import os
from typing import Dict

from typeguard import typechecked

from taskmates.actions.invoke_function import invoke_function
from taskmates.assistances.completion_assistance import CompletionAssistance
from taskmates.assistances.markdown.tool_editor_completion import ToolEditorCompletion
from taskmates.config import CompletionContext
from taskmates.function_registry import function_registry
from taskmates.model.tool_call import ToolCall
from taskmates.signals.signals import Signals
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

        editor_completion = ToolEditorCompletion(project_dir=cwd, chat_file=markdown_path, signals=signals)

        for tool_call in tool_calls:
            function_title = tool_call["function"]["name"].replace("_", " ").title()
            await editor_completion.append_tool_execution_header(function_title, tool_call["id"])

            tool_call_obj = ToolCall.from_dict(tool_call)

            async def handle_interrupted(sender):
                await signals.output.response.send_async("--- INTERRUPT ---\n")

            async def handle_killed(sender):
                await signals.output.response.send_async("--- KILL ---\n")

            with signals.output.interrupted.connected_to(handle_interrupted), \
                    signals.output.killed.connected_to(handle_killed):
                original_cwd = os.getcwd()
                try:
                    try:
                        os.chdir(cwd)
                    except FileNotFoundError:
                        pass
                    return_value = await self.execute_task(context, tool_call_obj, signals)
                finally:
                    os.chdir(original_cwd)

            await signals.output.response.send_async(str(return_value))
            await editor_completion.append_tool_execution_footer(function_title)

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
