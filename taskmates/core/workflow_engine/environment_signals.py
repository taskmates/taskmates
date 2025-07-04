from typing import TypedDict

from taskmates.core.workflows.signals.llm_chat_completion_signals import LlmChatCompletionSignals
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.core.workflows.signals.input_streams import InputStreams
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals


class EnvironmentSignals(TypedDict):
    control: ControlSignals
    status: StatusSignals
    input_streams: InputStreams
    execution_environment: ExecutionEnvironmentSignals
    markdown_completion: MarkdownCompletionSignals
