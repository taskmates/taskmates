from typing import List, Dict, Any
from taskmates.model.chat_message import ChatMessage
from taskmates.model.last_message import LastMessage

class Chat:
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.last_message: LastMessage = LastMessage()
        self.model: str = ""
        self.context: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.base_path: str = ""
        self.participants: List[str] = []
        self.available_tools: List[str] = []

    def is_echoed(self) -> bool:
        return self.messages[-1].name == "echo"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chat':
        chat = cls()
        chat.messages = [ChatMessage(**message) for message in data.get('messages', [])]
        chat.last_message = LastMessage(**data.get('last_message', {}))
        chat.model = data.get('model', '')
        chat.context = data.get('context', {})
        chat.metadata = data.get('metadata', {})
        chat.base_path = data.get('base_path', '')
        chat.participants = data.get('participants', [])
        chat.available_tools = data.get('available_tools', [])
        return chat
