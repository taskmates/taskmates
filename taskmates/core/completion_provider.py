from abc import ABC, abstractmethod

from taskmates.formats.openai.get_text_content import get_text_content
from taskmates.types import Chat


class CompletionProvider(ABC):
    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

    # TODO: we're missing a return type here
    # IDEA: make return type signal all side effects
    @abstractmethod
    async def perform_completion(self, chat: Chat):
        pass

    @staticmethod
    def has_truncated_response(chat: Chat) -> bool:
        if not chat["messages"]:
            return False

        last_message = chat["messages"][-1]
        role = last_message.get("role", "")

        # Messages from users or system are never resume requests
        if role in ("user", "system"):
            return False

        code_cells = last_message.get("code_cells", [])
        if code_cells:
            if code_cells[-1].get("metadata", {}).get("partial", False):
                return True

        return not get_text_content(last_message).endswith("\n")

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
            if code_cells[-1].get("metadata", {}).get("partial", False):
                return True

        return False
