from abc import ABC, abstractmethod

from typeguard import typechecked

from taskmates.types import Chat
from taskmates.core.workflows.signals.llm_chat_completion_signals import LlmChatCompletionSignals
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals


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
