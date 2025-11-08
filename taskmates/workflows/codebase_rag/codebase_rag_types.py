from typing import TypedDict, List

from pydantic import BaseModel


class SelectableItem(TypedDict):
    """Base type for items that can be selected (files or chunks)."""
    id: int
    uri: str  # "path/to/file.py" or "path/to/file.py:10-20"
    token_count: int


class FileChunk(TypedDict):
    """Represents a chunk of code from a file with text content."""
    id: int
    uri: str  # "path/to/file.py:10-20"
    text: str
    token_count: int


class SelectionResult(TypedDict):
    """Result from selecting items (files or chunks)."""
    selected_uris: List[str]  # Changed from selected_ids to selected_uris
    scratchpad: str


class NavigationResult(TypedDict):
    """Result from navigating to code snippets."""
    snippets: List[FileChunk]
    scratchpad: str


class ContextResult(TypedDict):
    """Result from gathering context (snippets and scratchpad)."""
    snippets: List[FileChunk]
    scratchpad: str


class AnswerResult(TypedDict):
    """Result from generating an answer."""
    answer: str
    citations: List[str]
    code_snippets: List[FileChunk]
    scratchpad: str


class SelectedChunks(BaseModel):
    """Schema for chunk selection."""
    chunk_ids: List[int]


class CodebaseAnswer(BaseModel):
    """Structured response for codebase questions."""
    answer: str
    citations: List[str]
