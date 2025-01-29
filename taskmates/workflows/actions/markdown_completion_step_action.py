from typeguard import typechecked

from taskmates.types import Chat
from taskmates.workflows.actions.taskmates_action import TaskmatesAction
from taskmates.workflows.signals.chat_completion_signals import ChatCompletionSignals
from taskmates.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.workflows.signals.status_signals import StatusSignals


@typechecked
class MarkdownCompleteSectionAction(TaskmatesAction):
    async def perform(
            self,
            chat: Chat,
            completion_assistance,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            chat_completion_signals: ChatCompletionSignals,
            code_cell_output_signals: CodeCellOutputSignals,
            status_signals: StatusSignals
    ):
        await completion_assistance.perform_completion(
            chat,
            control_signals,
            markdown_completion_signals,
            chat_completion_signals,
            code_cell_output_signals,
            status_signals
        )
