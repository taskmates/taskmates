import textwrap

import jupytext
from nbformat import NotebookNode


def parse_notebook(content: str) -> (NotebookNode, list[NotebookNode]):
    # Convert markdown to a Jupyter notebook with specific handling for .eval

    notebook = jupytext.reads(content, fmt="md")

    # Filter code cells to include only those marked with .eval
    code_cells = [cell for cell in notebook.cells
                  if cell.cell_type == "code"
                  and ".eval" in cell.metadata]

    if code_cells:
        # Workaround to prevent nbformat from parsing code cells from partial content (i.e. missing closing ```)
        if content.rstrip().endswith(code_cells[-1].source.rstrip()):
            code_cells[-1]["metadata"]["partial"] = True
            return notebook, code_cells

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
    assert code_cells[0].source == '\nprint("Hello, world!")'


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
