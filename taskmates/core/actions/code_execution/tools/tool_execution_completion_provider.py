import os
from typing import Dict

from typeguard import typechecked

from taskmates.actions.invoke_function import invoke_function
from taskmates.core.actions.code_execution.code_cells.code_execution import CodeExecution
from taskmates.core.actions.code_execution.tools.tool_editor_completion import ToolEditorCompletion
from taskmates.core.completion_provider import CompletionProvider
from taskmates.core.tools_registry import tools_registry
from taskmates.model.tool_call import ToolCall
from taskmates.core.execution_context import EXECUTION_CONTEXT, ExecutionContext
from taskmates.types import Chat, CompletionContext


class ToolExecutionCompletionProvider(CompletionProvider):
    def can_complete(self, chat: Dict) -> bool:
        messages = chat.get("messages", [])
        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", [])
        return len(tool_calls) > 0

    async def perform_completion(self, chat: Chat):
        contexts = EXECUTION_CONTEXT.get().contexts
        execution_context = EXECUTION_CONTEXT.get()

        completion_context = contexts["completion_context"]
        cwd = completion_context["cwd"]
        markdown_path = completion_context["markdown_path"]

        messages = chat.get("messages", [])

        tool_calls = messages[-1].get("tool_calls", [])

        editor_completion = ToolEditorCompletion(project_dir=cwd, chat_file=markdown_path, execution_context=execution_context)

        for tool_call in tool_calls:
            function_title = tool_call["function"]["name"].replace("_", " ").title()
            await editor_completion.append_tool_execution_header(function_title, tool_call["id"])

            tool_call_obj = ToolCall.from_dict(tool_call)

            async def handle_interrupted(sender):
                await execution_context.outputs.response.send_async("--- INTERRUPT ---\n")

            async def handle_killed(sender):
                await execution_context.outputs.response.send_async("--- KILL ---\n")

            with execution_context.status.interrupted.connected_to(handle_interrupted), \
                    execution_context.status.killed.connected_to(handle_killed):
                original_cwd = os.getcwd()
                try:
                    try:
                        os.chdir(cwd)
                    except FileNotFoundError:
                        pass
                    return_value = await self.execute_task(completion_context, tool_call_obj, execution_context)
                finally:
                    os.chdir(original_cwd)

            await execution_context.outputs.response.send_async(CodeExecution.escape_pre_output(str(return_value)))
            await editor_completion.append_tool_execution_footer(function_title)

    @staticmethod
    @typechecked
    async def execute_task(context: CompletionContext, tool_call: ToolCall, execution_context: ExecutionContext):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments

        child_context = context.copy()
        child_context["env"] = context["env"].copy()
        child_context["env"]["TOOL_CALL_ID"] = tool_call_id

        function = tools_registry[function_name]
        return_value = await invoke_function(function, arguments, child_context, execution_context)

        return return_value
