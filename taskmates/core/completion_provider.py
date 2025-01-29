from abc import ABC, abstractmethod

from typeguard import typechecked

from taskmates.types import Chat
from taskmates.workflows.signals.chat_completion_signals import ChatCompletionSignals
from taskmates.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.workflows.signals.status_signals import StatusSignals


@typechecked
class CompletionProvider(ABC):
    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

    @abstractmethod
    async def perform_completion(
            self,
            chat: Chat,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            chat_completion_signals: ChatCompletionSignals,
            code_cell_output_signals: CodeCellOutputSignals,
            status_signals: StatusSignals
    ):
        pass

    @staticmethod
    def has_truncated_code_cell(chat: Chat) -> bool:
        if not chat["messages"]:
            return False

        last_message = chat["messages"][-1]
        role = last_message.get("role", "")

        # Messages from users or system are never resume requests
        if role in ("user", "system"):
            return False

        code_cells = last_message.get("code_cells", [])
        if code_cells:
            if code_cells[-1].get("truncated", False):
                return True

        return False
