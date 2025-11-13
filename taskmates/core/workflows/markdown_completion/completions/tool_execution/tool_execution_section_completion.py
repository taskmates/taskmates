import os

from typeguard import typechecked

from taskmates.core.tools_registry import tools_registry
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transaction import Transaction, TRANSACTION
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.code_execution import \
    CodeExecution
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.markdown_completion.completions.section_completion import SectionCompletion
from taskmates.core.workflows.markdown_completion.completions.tool_execution.invoke_function import invoke_function
from taskmates.core.workflows.markdown_completion.completions.tool_execution.response.tool_execution_appender import \
    ToolExecutionAppender
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.runtimes.cli.collect_markdown_bindings import CollectMarkdownBindings
from taskmates.types import CompletionRequest, RunnerEnvironment, ToolCall


@typechecked
class ToolExecutionSectionCompletion(SectionCompletion):
    def can_complete(self, chat: CompletionRequest) -> bool:
        messages = chat.get("messages", [])
        if has_truncated_code_cell(messages[-1]):
            return False

        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", [])
        return len(tool_calls) > 0

    @transactional
    async def perform_completion(self, chat: CompletionRequest) -> str:
        markdown_chat_state = MarkdownChat()

        async with CollectMarkdownBindings(runtime.transaction, markdown_chat_state):
            control_signals: ControlSignals = runtime.transaction.emits["control"]
            execution_environment_signals: ExecutionEnvironmentSignals = runtime.transaction.consumes[
                "execution_environment"]
            status_signals: StatusSignals = runtime.transaction.consumes["status"]

            messages = chat.get("messages", [])

            contexts = TRANSACTION.get().context
            run = TRANSACTION.get()

            runner_environment = contexts["runner_environment"]
            cwd = runner_environment["cwd"]
            markdown_path = runner_environment["markdown_path"]

            tool_calls = messages[-1].get("tool_calls", [])

            editor_completion = ToolExecutionAppender(project_dir=cwd, chat_file=markdown_path,
                                                      execution_environment_signals=execution_environment_signals)

            for tool_call in tool_calls:
                function_title = tool_call["function"]["name"].replace("_", " ").title()
                await editor_completion.append_tool_execution_header(function_title, tool_call["id"])

                tool_call_obj = ToolCall.from_dict(tool_call)

                async def handle_interrupted(sender):
                    await execution_environment_signals.response.send_async(sender="response",
                                                                            value="--- INTERRUPT ---\n")

                async def handle_killed(sender):
                    await execution_environment_signals.response.send_async(sender="response", value="--- KILL ---\n")

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

                await execution_environment_signals.response.send_async(sender="response",
                                                                        value=CodeExecution.escape_pre_output(
                                                                            str(return_value)))
                await editor_completion.append_tool_execution_footer(function_title)

        return markdown_chat_state.get()["completion"]

    @staticmethod
    @typechecked
    async def execute_task(context: RunnerEnvironment, tool_call: ToolCall, run: Transaction):
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments

        if tuple(arguments.keys()) == ("kwargs",):
            arguments = arguments["kwargs"]

        child_context = context.copy()
        child_context["env"] = {**context["env"]}
        child_context["env"]["TOOL_CALL_ID"] = tool_call_id

        function = tools_registry[function_name]
        return_value = await invoke_function(function, arguments, child_context, run)

        return return_value
