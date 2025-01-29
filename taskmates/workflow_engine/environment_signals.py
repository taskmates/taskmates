from typing import TypedDict

from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.input_streams import InputStreams
from taskmates.workflows.signals.status_signals import StatusSignals
from taskmates.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.workflows.signals.chat_completion_signals import ChatCompletionSignals
from taskmates.workflows.signals.code_cell_output_signals import CodeCellOutputSignals


class EnvironmentSignals(TypedDict):
    control: ControlSignals
    status: StatusSignals
    input_streams: InputStreams
    execution_environment: ExecutionEnvironmentSignals
    markdown_completion: MarkdownCompletionSignals
    chat_completion: ChatCompletionSignals
    code_cell_output: CodeCellOutputSignals
