from typing import Any, Optional, List

from taskmates.lib.not_set.not_set import NOT_SET


class ReturnValue:
    def __init__(self):
        super().__init__()
        self._stdout_chunks: List[str] = []
        self._return_value: Any = NOT_SET
        self._error: Optional[Exception] = None

    def get_stdout_chunks(self) -> List[str]:
        return self._stdout_chunks

    def append_stdout_chunk(self, chunk: str) -> None:
        self._stdout_chunks.append(chunk)

    def get_return_value(self) -> Any:
        return self._return_value

    def set_return_value(self, value: Any) -> None:
        self._return_value = value

    def get_error(self) -> Optional[Exception]:
        return self._error

    def set_error(self, error: Exception) -> None:
        self._error = error

    def get(self):
        return self._return_value
