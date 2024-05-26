from typing import Optional, Union, List, Any

from pydantic import BaseModel


class DeltaModel(BaseModel):
    content: Optional[Union[str, List]] = None
    function_call: Optional[Any] = None
    role: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List] = None
