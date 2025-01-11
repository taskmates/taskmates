from abc import ABC, abstractmethod

from taskmates.types import Chat


class CompletionProvider(ABC):
    @abstractmethod
    def can_complete(self, chat: Chat):
        pass

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

        content = last_message.get("content", "")

        # If content is a list (e.g., for images), we need to get the last text content
        if isinstance(content, list):
            text_contents = [item["text"] for item in content if item.get("type") == "text"]
            if not text_contents:
                return False
            content = text_contents[-1]

        code_cells = last_message.get("code_cells", [])
        if code_cells:
            if code_cells[-1].get("metadata", {}).get("partial", False):
                return True

        return not content.endswith("\n")
