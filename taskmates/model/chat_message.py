from typing import List, Dict, Any, Optional

from taskmates.model.tool_call import ToolCall


class ChatMessage:
    def __init__(self, role: str, content: Optional[str] = None, name: Optional[str] = None,
                 tool_call_id: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None,
                 tool_calls: Optional[List[ToolCall]] = None):
        self.role: str = role
        self.name: Optional[str] = name
        self.content: Optional[str] = content
        self.tool_call_id: Optional[str] = tool_call_id
        self.tool_calls: Optional[List[ToolCall]] = tool_calls

        if attributes is not None:
            self.name = attributes.get("name", None)
            self.tool_call_id = attributes.get("tool_call_id", None)

        if tool_calls is not None:
            self.role = "system"
            self.name = "ide"

    @staticmethod
    def build_tool_call_message(function_name: str, key: str, value: str) -> 'ChatMessage':
        arguments = {
            "key": key,
            "value": value
        }
        return ChatMessage.build_tool_call_message(function_name, arguments)

    @staticmethod
    def build_tool_call_message(function_name: str, arguments: Dict[str, Any]) -> 'ChatMessage':
        tool_calls = []
        set_chat_dir_path = ToolCall()
        set_chat_dir_path.type = "function"
        set_chat_dir_path_function = ToolCall.Function()
        set_chat_dir_path.function = set_chat_dir_path_function
        set_chat_dir_path_function.name = function_name
        set_chat_dir_path_function.arguments_map = arguments
        tool_calls.append(set_chat_dir_path)
        return ChatMessage(role="system", tool_calls=tool_calls)

    def append(self, text: str) -> None:
        self.content += text

    def get_text_content(self) -> str:
        return self.content or ""

    def is_user_prompt(self) -> bool:
        return self.role == "user" and (self.content is None or str(self.content).strip() == "")
