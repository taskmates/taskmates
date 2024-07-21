import argparse
import json
import sys
import textwrap

import pytest
from jupyter_client import KernelManager
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from nbconvert.filters import strip_ansi
from nbformat import NotebookNode

from taskmates.core.code_execution.code_cells.jupyter_enterprise_gateway_client import get_kernel_manager, \
    DEFAULT_GATEWAY_URL
from taskmates.core.code_execution.code_cells.parse_notebook import parse_notebook


async def setup_kernel(kernel_manager, cwd=None):
    setup_code = ""
    # setup_code = textwrap.dedent("""\
    # ```python .eval
    # %load_ext taskmates.magics.file_editing_magics
    # ```
    # """)

    if cwd is not None:
        setup_code += textwrap.dedent(f"""\
        ```python .eval
        %cd {cwd}
        ```
        """)

    notebook, code_cells = parse_notebook(setup_code)
    client = NotebookClient(nb=notebook, km=kernel_manager, allow_errors=False)

    async with client.async_setup_kernel(**{}):
        for index, cell in enumerate(code_cells):
            await client.async_execute_cell(cell, index)


# Main execution function
async def execute_markdown_on_enterprise_gateway(content, kernel_manager=None, path=None, kernel_id=None, cwd=None):
    if kernel_manager is None:
        kernel_manager = await get_kernel_manager(gateway_url=DEFAULT_GATEWAY_URL, path=path, kernel_id=kernel_id)

    notebook: NotebookNode
    code_cells: list[NotebookNode]

    if not hasattr(kernel_manager, 'setup_done'):
        await setup_kernel(kernel_manager, cwd)
        kernel_manager.setup_done = True

    notebook, code_cells = parse_notebook(content)

    # Create a NotebookClient with the KernelManager
    # TODO: try resources = {"metadata": {"path": "/opt"}}
    client = NotebookClient(nb=notebook, km=kernel_manager, allow_errors=False)

    try:
        async with client.async_setup_kernel(**{}):
            try:
                for index, cell in enumerate(code_cells):
                    await client.async_execute_cell(cell, index)
            except CellExecutionError:
                pass

    finally:
        if client.kc:
            client.kc.stop_channels()
    # Format output
    return format_output(code_cells)


# Function to format the output of executed code cells
def format_output(code_cells):
    outputs_and_errors = []
    for cell in code_cells:
        outputs = cell.outputs

        for output in outputs:
            output.pop("execution_count", None)
            output.pop("metadata", None)
            if output.artifact_type == "error":
                output["traceback"] = list(map(strip_ansi, output["traceback"]))
            if output.get("text") is not None:
                output["text"] = strip_ansi(output['text'])

        cell_dict = {
            "id": cell.metadata.get("id", ""),
            "cell_type": cell.cell_type,
            "source": cell.source,
            "outputs": outputs
        }

        outputs_and_errors.append(cell_dict)

    return outputs_and_errors


async def main(argv=None):
    # Use argv if provided, else use sys.argv
    if argv is None:
        argv = sys.argv[1:]

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Execute markdown as Jupyter notebook.")
    parser.add_argument("--content", type=str, help="Markdown string to execute.")
    parser.add_argument("--path", type=str, help="Path to the Jupyter notebook.")
    parser.add_argument("--kernel_id", type=str, help="Kernel ID to use.")
    parser.add_argument("--gateway_url", type=str, default=DEFAULT_GATEWAY_URL,
                        help="URL of the Jupyter Enterprise Gateway.")
    parser.add_argument("--cwd", type=str, help="Current working directory for the notebook execution.")
    args = parser.parse_args(argv)

    if args.kernel_id is None and args.path is None:
        raise ValueError("Either kernel_id or path must be provided.")

    # Execute markdown
    result = await execute_markdown_on_enterprise_gateway(content=args.content, path=args.path,
                                                          kernel_id=args.kernel_id, cwd=args.cwd)

    # Print result
    print(json.dumps(result, ensure_ascii=False))


@pytest.fixture(scope="module")
async def shared_kernel_manager():
    km = KernelManager(kernel_name='python3')
    print("starting kernel")
    km.start_kernel()

    yield km

    # Shutdown the kernel after the tests are done
    print("stopping kernel")
    km.shutdown_kernel(now=True)
    km.cleanup()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_markdown_code_cells_no_code(shared_kernel_manager):
    input_md = textwrap.dedent("""\
        # This is a markdown text

        This is a paragraph.
    """)
    expected_output = []
    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager)
    assert output == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_markdown_code_cells_simple_code(shared_kernel_manager):
    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + 3
        x
        ```
    """)
    expected_output = [
        {
            "id": "",
            "cell_type": "code",
            "source": "x = 2 + 3\nx",
            "outputs": [
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": "5"
                    }
                }
            ]
        }
    ]
    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager)
    assert output == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_markdown_code_cells_error_code(shared_kernel_manager):
    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + '3'
        ```
    """)
    expected_output = [{'cell_type': 'code',
                        'id': '',
                        'outputs': [{'ename': 'TypeError',
                                     'evalue': "unsupported operand type(s) for +: 'int' and 'str'",
                                     'output_type': 'error',
                                     'traceback': [
                                         '---------------------------------------------------------------------------',
                                         'TypeError                                 '
                                         'Traceback (most recent call last)',
                                         "Cell In[2], line 1\n----> 1 x = 2 + '3'\n",
                                         'TypeError: unsupported operand type(s) for +: '
                                         "'int' and 'str'"]}],
                        'source': "x = 2 + '3'"}]

    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager)
    assert output == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_markdown_code_cells_multiple_cells(shared_kernel_manager):
    input_md = textwrap.dedent("""\
        # Markdown with multiple code cells

        ```python .eval
        x = 2 + 3
        x
        ```

        ```python .eval
        y = x * 2
        y
        ```
    """)
    expected_output = [
        {
            "id": "",
            "cell_type": "code",
            "source": "x = 2 + 3\nx",
            "outputs": [
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": "5"
                    }
                }
            ]
        },
        {
            "id": "",
            "cell_type": "code",
            "source": "y = x * 2\ny",
            "outputs": [
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": "10"
                    }
                }
            ]
        }
    ]
    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager)
    assert output == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_main_execution(capsys, tmp_path):
    # Create a temporary markdown file with code
    markdown_content = textwrap.dedent("""\
        ```python .eval
        x = 2 + 3
        x
        ```
    """)
    markdown_file = tmp_path / "test.md"
    markdown_file.write_text(markdown_content)

    # Prepare the arguments to pass to main
    test_args = [
        "--content", markdown_content,  # content
        "--path", str(markdown_file)  # path
    ]

    # Call main with the test arguments
    await main(test_args)

    captured = capsys.readouterr()

    captured_out = captured.out
    print(captured_out)
    parsed_out = json.loads(captured_out)
    assert parsed_out == [
        {
            "id": "",
            "cell_type": "code",
            "source": "x = 2 + 3\nx",
            "outputs": [
                {
                    "output_type": "execute_result",
                    "data": {
                        "text/plain": "5"
                    }
                }
            ]
        }
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_markdown_with_cwd(shared_kernel_manager, tmp_path):
    # Create a temporary directory and a file in it
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test_file.txt"
    test_file.write_text("Hello, World!")

    # Markdown content that reads the file
    input_md = textwrap.dedent(f"""\
        ```python .eval
        with open("{test_file}", "r") as f:
            content = f.read()
        print(content)
        ```
    """)

    # Execute the markdown with cwd set to the temporary directory
    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager, cwd=str(test_dir))

    # Check if the output contains the expected file content
    assert output[0]["outputs"][0]["text"] == "Hello, World!\n"

    # Execute the markdown again without changing the cwd
    output = await execute_markdown_on_enterprise_gateway(input_md, shared_kernel_manager)

    # Check if the output still contains the expected file content
    assert output[0]["outputs"][0]["text"] == "Hello, World!\n"
