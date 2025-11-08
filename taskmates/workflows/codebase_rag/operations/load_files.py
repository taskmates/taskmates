from pathlib import Path
from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import FileChunk, SelectableItem
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens


@transactional
async def load_files(
    project_root: str,
    file_pattern: str = "*.py",
    selected_items: List[SelectableItem] = None
) -> List[FileChunk]:
    """
    Load files and convert them to FileChunks with text content.

    Takes SelectableItems (file-level) and returns FileChunks (with text).
    Updates URIs from "path/to/file.py" to "path/to/file.py:1-N".

    Args:
        project_root: Root directory of the project
        file_pattern: Glob pattern for files to load (default: "*.py")
        selected_items: List of SelectableItems to load (if None, loads all matching files)

    Returns:
        List of FileChunks with text content and updated URIs
    """
    project_path = Path(project_root)

    exclude_patterns = {
        '__pycache__', '.pyc', 'venv', '.venv', 'site-packages',
        '.git', '.pytest_cache', '.tox', 'build', 'dist', '.eggs'
    }

    chunks: List[FileChunk] = []

    if selected_items is not None:
        files_to_load = [(item['id'], project_path / item['uri']) for item in selected_items]
    else:
        files_to_load = [(i, fp) for i, fp in enumerate(project_path.rglob(file_pattern))]

    for chunk_id, py_file in files_to_load:
        if not py_file.is_file():
            continue

        if any(excluded in py_file.parts for excluded in exclude_patterns):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rel_path = py_file.relative_to(project_path)

            lines = content.split('\n')
            line_count = len(lines)
            token_count = count_tokens(content)

            # Create URI with line numbers
            uri = f"{rel_path}:1-{line_count}"

            chunks.append({
                'id': chunk_id,
                'uri': uri,
                'text': content,
                'token_count': token_count
            })

        except Exception as e:
            runtime.logger.warning(f"Could not read {py_file}: {e}")
            continue

    runtime.logger.info(f"Loaded {len(chunks)} files matching pattern '{file_pattern}'")
    return chunks
