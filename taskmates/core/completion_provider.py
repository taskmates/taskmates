from abc import ABC, abstractmethod

from taskmates.types import Chat
from taskmates.workflow_engine.environment_signals import EnvironmentSignals


class CompletionProvider(ABC):
    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

    @abstractmethod
    async def perform_completion(self, chat: Chat, completion_signals: EnvironmentSignals):
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
