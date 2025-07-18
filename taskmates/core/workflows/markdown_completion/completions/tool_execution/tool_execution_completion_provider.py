import os
from typing import Dict

from typeguard import typechecked

from taskmates.core.tools_registry import tools_registry
from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflow_engine.run import Run
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.code_execution import \
    CodeExecution
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.completions.tool_execution.invoke_function import invoke_function
from taskmates.core.workflows.markdown_completion.completions.tool_execution.response.tool_execution_appender import \
    ToolExecutionAppender
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import Chat, RunnerEnvironment, ToolCall


@typechecked
class ToolExecutionCompletionProvider(CompletionProvider):
    def can_complete(self, chat: Dict) -> bool:
        if self.has_truncated_code_cell(chat):
            return False

        messages = chat.get("messages", [])
        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", [])
        return len(tool_calls) > 0

    async def perform_completion(
            self,
            chat: Chat,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            status_signals: StatusSignals
    ):
        contexts = RUN.get().context
        run = RUN.get()

        runner_environment = contexts["runner_environment"]
        cwd = runner_environment["cwd"]
        markdown_path = runner_environment["markdown_path"]

        messages = chat.get("messages", [])

        tool_calls = messages[-1].get("tool_calls", [])

        editor_completion = ToolExecutionAppender(project_dir=cwd, chat_file=markdown_path,
                                                  markdown_completion_signals=markdown_completion_signals)

        for tool_call in tool_calls:
            function_title = tool_call["function"]["name"].replace("_", " ").title()
            await editor_completion.append_tool_execution_header(function_title, tool_call["id"])

            tool_call_obj = ToolCall.from_dict(tool_call)

            async def handle_interrupted(sender):
                await markdown_completion_signals.response.send_async("--- INTERRUPT ---\n")

            async def handle_killed(sender):
                await markdown_completion_signals.response.send_async("--- KILL ---\n")

            with status_signals.interrupted.connected_to(handle_interrupted), \
                    status_signals.killed.connected_to(handle_killed):
                original_cwd = os.getcwd()
                try:
                    try:
                        os.chdir(cwd)
                    except FileNotFoundError:
                        pass
                    return_value = await self.execute_task(runner_environment, tool_call_obj, run)
                finally:
                    os.chdir(original_cwd)

            await markdown_completion_signals.response.send_async(CodeExecution.escape_pre_output(str(return_value)))
            await editor_completion.append_tool_execution_footer(function_title)

    @staticmethod
    @typechecked
    async def execute_task(context: RunnerEnvironment, tool_call: ToolCall, run: Run):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments

        child_context = context.copy()
        child_context["env"] = {**context["env"]}
        child_context["env"]["TOOL_CALL_ID"] = tool_call_id

        function = tools_registry[function_name]
        return_value = await invoke_function(function, arguments, child_context, run)

        return return_value
