from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk


def filter_selected_chunks(
        chunks: List[FileChunk],
        selected_uris: List[str]
) -> List[FileChunk]:
    """
    Filter chunks to only those with URIs in the selected list.
    
    Args:
        chunks: List of all chunks
        selected_uris: List of URIs to keep
        
    Returns:
        List of chunks with matching URIs
    """
    return [chunk for chunk in chunks if chunk['uri'] in selected_uris]
