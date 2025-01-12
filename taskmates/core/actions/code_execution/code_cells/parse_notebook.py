import textwrap
import re

import jupytext
from nbformat import NotebookNode

from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger


def parse_notebook(content: str) -> (NotebookNode, list[NotebookNode]):
    # Convert markdown to a Jupyter notebook with specific handling for .eval
    jupyter_notebook_logger.debug(f"Parsing markdown content:\n{content}")
    notebook = jupytext.reads(content, fmt="md")
    jupyter_notebook_logger.debug(f"Found {len(notebook.cells)} cells in total")

    # Find all code blocks with .eval in the original markdown
    eval_blocks = re.finditer(r'```python\s+\.eval\n(.*?)```', content, re.DOTALL)
    eval_sources = {block.group(1).strip() for block in eval_blocks}
    jupyter_notebook_logger.debug(f"Found eval blocks: {eval_sources}")

    # Filter code cells to include only those that match the eval blocks
    code_cells = []
    for cell in notebook.cells:
        jupyter_notebook_logger.debug(f"Processing cell type: {cell.cell_type}")
        if cell.cell_type == "code":
            jupyter_notebook_logger.debug(f"Code cell source:\n{cell.source}")
            if cell.source.strip() in eval_sources:
                jupyter_notebook_logger.debug("Found matching eval block")
                # Mark the cell with .eval in metadata
                if 'metadata' not in cell:
                    cell['metadata'] = {}
                cell.metadata['.eval'] = True
                code_cells.append(cell)

    jupyter_notebook_logger.debug(f"Found {len(code_cells)} code cells with .eval")

    if code_cells:
        # Workaround to prevent nbformat from parsing code cells from partial content (i.e. missing closing ```)
        if content.rstrip().endswith(code_cells[-1].source.rstrip()):
            code_cells[-1]["metadata"]["partial"] = True

    return notebook, code_cells


# Test with markdown content that contains code cells marked with .eval
def test_parse_notebook_with_eval_code_cells():
    markdown_content = """
    ```python .eval
    print("Hello, world!")
    ```
    """
    notebook, code_cells = parse_notebook(textwrap.dedent(markdown_content))
    assert len(code_cells) == 1
    assert "Hello, world!" in code_cells[0].source
    assert code_cells[0].metadata['.eval'] is True


# Test with markdown content that contains code cells but without .eval
def test_parse_notebook_without_eval_code_cells():
    markdown_content = """
    ```python
    print("This should not be evaluated.")
    ```
    """
    notebook, code_cells = parse_notebook(textwrap.dedent(markdown_content))
    assert len(code_cells) == 0


# Test with markdown content that does not contain any code cells
def test_parse_notebook_without_code_cells():
    markdown_content = """
This is a markdown document without any code cells.
"""
    notebook, code_cells = parse_notebook(markdown_content)
    assert len(code_cells) == 0


# Test with empty markdown content
def test_parse_notebook_empty_content():
    markdown_content = ""
    notebook, code_cells = parse_notebook(markdown_content)
    assert len(code_cells) == 0
