from typing import List, Set

from pydantic import BaseModel, Field, field_validator


def create_file_selection_schema(valid_uris: Set[str]) -> type[BaseModel]:
    """
    Create a FileSelectionResult schema with validation for specific valid URIs.

    Args:
        valid_uris: Set of valid file URIs that can be selected

    Returns:
        Pydantic model class with URI validation
    """

    class FileSelectionResult(BaseModel):
        """Schema for file selection with URI validation."""
        reasoning: str = Field(description="Explanation of why these files are relevant")
        selected_files: List[str] = Field(description="List of selected file URIs (paths)")

        @field_validator('selected_files')
        @classmethod
        def validate_uris(cls, v: List[str]) -> List[str]:
            """Validate that all selected URIs exist in the valid set."""
            invalid_uris = [uri for uri in v if uri not in valid_uris]
            if invalid_uris:
                valid_list = "\n".join(f"  - {uri}" for uri in sorted(valid_uris))
                raise ValueError(
                    f"The following URIs are not valid. You MUST select ONLY from the provided list.\n"
                    f"Invalid URIs: {invalid_uris}\n\n"
                    f"Valid URIs to choose from:\n{valid_list}"
                )

            return v

    return FileSelectionResult


def create_chunk_selection_schema(valid_uris: Set[str]) -> type[BaseModel]:
    """
    Create a ChunkSelectionResult schema with validation for specific valid URIs.

    Args:
        valid_uris: Set of valid chunk URIs that can be selected

    Returns:
        Pydantic model class with URI validation
    """

    class ChunkSelectionResult(BaseModel):
        """Schema for chunk selection with URI validation."""
        reasoning: str = Field(description="Explanation of why these chunks are relevant")
        selected_chunks: List[str] = Field(description="List of selected chunk URIs (file:line_start-line_end)")

        @field_validator('selected_chunks')
        @classmethod
        def validate_uris(cls, v: List[str]) -> List[str]:
            """Validate that all selected URIs exist in the valid set."""
            invalid_uris = [uri for uri in v if uri not in valid_uris]
            if invalid_uris:
                valid_list = "\n".join(f"  - {uri}" for uri in sorted(valid_uris))
                raise ValueError(
                    f"The following URIs are not valid. You MUST select ONLY from the provided list.\n"
                    f"Invalid URIs: {invalid_uris}\n\n"
                    f"Valid URIs to choose from:\n{valid_list}"
                )

            return v

    return ChunkSelectionResult
