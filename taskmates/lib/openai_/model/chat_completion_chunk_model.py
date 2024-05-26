from typing import Optional, List

from pydantic import BaseModel
from taskmates.lib.openai_.model.choice_model import ChoiceModel


class ChatCompletionChunkModel(BaseModel):
    id: Optional[str] = None
    choices: List[ChoiceModel]
    created: Optional[int] = None
    model: str
    object: str = 'chat.completion.chunk'
    system_fingerprint: Optional[str] = None
