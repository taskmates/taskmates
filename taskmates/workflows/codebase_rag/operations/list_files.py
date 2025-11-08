from pathlib import Path
from typing import List

from taskmates.workflows.codebase_rag.codebase_rag_types import SelectableItem
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.utils.count_tokens import count_tokens


@transactional
async def list_files(project_root: str, file_pattern: str = "*.py") -> List[SelectableItem]:
    """
    List all files matching the pattern from the project directory without loading content.

    Returns SelectableItems with file URIs (no line numbers yet).

    Args:
        project_root: Root directory of the project
        file_pattern: Glob pattern for files to load (default: "*.py")

    Returns:
        List of SelectableItems representing files
    """
    project_path = Path(project_root)

    exclude_patterns = {
        '__pycache__', '.pyc', 'venv', '.venv', 'site-packages',
        '.git', '.pytest_cache', '.tox', 'build', 'dist', '.eggs'
    }

    file_items: List[SelectableItem] = []
    file_id = 0

    for file_path in project_path.rglob(file_pattern):
        if not file_path.is_file():
            continue

        if any(excluded in file_path.parts for excluded in exclude_patterns):
            continue

        rel_path = file_path.relative_to(project_path)

        # Estimate token count based on file size (rough estimate: 1 token per 4 bytes)
        try:
            file_size = file_path.stat().st_size
            estimated_tokens = file_size // 4
        except Exception:
            estimated_tokens = 1000  # Default estimate if we can't read file size

        file_items.append({
            'id': file_id,
            'uri': str(rel_path),
            'token_count': estimated_tokens
        })
        file_id += 1

    runtime.logger.info(f"Found {len(file_items)} files matching pattern '{file_pattern}'")
    return file_items
