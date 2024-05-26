from typing import Optional, Any

from pydantic import BaseModel
from taskmates.lib.openai_.model.delta_model import DeltaModel


class ChoiceModel(BaseModel):
    delta: DeltaModel
    finish_reason: Optional[str] = None
    index: int = 0
    logprobs: Optional[Any] = None
