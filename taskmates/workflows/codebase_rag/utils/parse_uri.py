def parse_chunk_uri(uri: str) -> tuple[str, int, int]:
    """
    Parse a chunk URI to extract path and line numbers.
    
    Args:
        uri: Chunk URI in format "path/to/file.py:10-20"
        
    Returns:
        Tuple of (path, line_start, line_end)
        
    Raises:
        ValueError: If URI is not in chunk format (missing line numbers)
    """
    if ':' not in uri:
        raise ValueError(f"URI '{uri}' is not a chunk URI (missing line numbers)")
    
    path, lines = uri.split(':', 1)
    
    if '-' not in lines:
        raise ValueError(f"URI '{uri}' has invalid line number format (expected 'start-end')")
    
    start, end = map(int, lines.split('-'))
    return path, start, end
