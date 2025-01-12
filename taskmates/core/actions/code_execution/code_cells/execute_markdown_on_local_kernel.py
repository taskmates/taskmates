import argparse
import asyncio
import os
import signal
import sys
import tempfile
import textwrap
from queue import Empty
from typing import Mapping

import pytest
from jupyter_client import AsyncKernelManager, AsyncKernelClient
from nbformat import NotebookNode

from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger
from taskmates.core.actions.code_execution.code_cells.parse_notebook import parse_notebook
from taskmates.lib.root_path.root_path import root_path
from taskmates.workflow_engine.run import RUN, Run

from taskmates.core.actions.code_execution.code_cells.kernel_manager import KernelManager
from taskmates.core.actions.code_execution.code_cells.message_handler import MessageHandler
from taskmates.core.actions.code_execution.code_cells.bash_script_handler import BashScriptHandler
from taskmates.core.actions.code_execution.code_cells.cell_executor import CellExecutor
from taskmates.core.actions.code_execution.code_cells.signal_handler import SignalHandler

kernel_manager = KernelManager()
bash_script_handler = BashScriptHandler()

pytestmark = pytest.mark.slow


# Main execution function
async def execute_markdown_on_local_kernel(content, markdown_path: str = None, cwd: str = None, env: Mapping = None):
    run: Run = RUN.get()
    status = run.signals["status"]
    control = run.signals["control"]
    output_streams = run.signals["output_streams"]

    jupyter_notebook_logger.debug(f"Starting execution for markdown_path={markdown_path}, cwd={cwd}")

    notebook: NotebookNode
    code_cells: list[NotebookNode]
    notebook, code_cells = parse_notebook(content)

    jupyter_notebook_logger.debug(f"Parsed {len(code_cells)} code cells")

    kernel_manager, kernel_client, setup_msgs = await get_or_start_kernel(cwd, markdown_path, env)

    message_handler = MessageHandler(kernel_client, run)
    await message_handler.start()

    signal_handler = SignalHandler(kernel_manager, message_handler, run)

    with control.interrupt.connected_to(signal_handler.handle_interrupt), \
            control.kill.connected_to(signal_handler.handle_kill):

        try:
            cell_executor = CellExecutor(message_handler, bash_script_handler, run)
            for cell_index, cell in enumerate(code_cells):
                should_continue = await cell_executor.execute_cell(cell, cell_index, len(code_cells), setup_msgs)
                if not should_continue:
                    break
        finally:
            jupyter_notebook_logger.debug("Cleaning up kernel resources: started")
            message_handler.cancel_tasks()
            kernel_client.stop_channels()
            jupyter_notebook_logger.debug("Cleaning up kernel resources: done")


async def get_or_start_kernel(cwd, markdown_path, env=None):
    return await kernel_manager.get_or_start_kernel(cwd, markdown_path, env)


async def main(argv=None):
    # Use argv if provided, else use sys.argv
    if argv is None:
        argv = sys.argv[1:]

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Execute markdown as Jupyter notebook.")
    parser.add_argument("--content", type=str, help="Markdown string to execute.")
    parser.add_argument("--markdown-path", type=str, help="Path associated with the kernel.")
    parser.add_argument("--cwd", type=str, help="Current working directory for the notebook execution.")
    args = parser.parse_args(argv)

    # Execute markdown
    await execute_markdown_on_local_kernel(content=args.content, markdown_path=args.path,
                                           cwd=args.cwd)


async def test_code_cells_no_code():
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        # This is a markdown text

        This is a paragraph.
    """)
    await execute_markdown_on_local_kernel(input_md, markdown_path="test_no_code")
    assert chunks == []


async def test_single_cell():
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + 3
        x
        ```
    """)
    await execute_markdown_on_local_kernel(input_md, markdown_path="test_simple_code")

    assert len(chunks) > 0

    assert len({chunk["msg_id"] for chunk in chunks}) == 1


async def test_multiple_cells(tmp_path):
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    content = textwrap.dedent("""\
    One cell:
    
    ```python .eval
    print("Hello")
    ```
    
    Another cell:

    ```python .eval
    print("World")
    ```
    """)

    await execute_markdown_on_local_kernel(content, markdown_path=str(tmp_path))

    assert len({chunk["msg_id"] for chunk in chunks}) == 2


async def test_cell_error():
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + '3'
        ```

        ```python .eval
        print("It should not reach here!")
        ```

    """)
    await execute_markdown_on_local_kernel(input_md, markdown_path="test_error_code")

    assert 'error' in [chunk['msg']['msg_type'] for chunk in chunks]


async def test_cwd(tmp_path):
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    # Markdown content that gets the current working directory
    input_md = textwrap.dedent(f"""\
        ```python .eval
        import os
        print(os.getcwd())
        ```
    """)

    # Execute the markdown with cwd set to the temporary directory
    await execute_markdown_on_local_kernel(input_md, markdown_path="test_with_cwd", cwd=str(tmp_path))

    # Check if the output contains the expected directory path
    output_path = chunks[-1]['msg']['content']['text'].strip()
    expected_path = str(tmp_path)

    # Normalize paths for comparison
    assert os.path.normpath(output_path) == os.path.normpath(expected_path)


async def test_interrupt(capsys):
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        import time
        for i in range(5):
            print(i)
            if i == 2:
                time.sleep(5)
        ```
    """)

    async def send_interrupt():
        while True:
            await asyncio.sleep(0.1)
            content = "".join([chunk['msg']['content']["text"]
                               for chunk in chunks
                               if chunk['msg']['msg_type'] == 'stream'])
            lines = content.split("\n")
            if len(lines) >= 2:
                break
        await run.signals["control"].interrupt.send_async(None)

    interrupt_task = asyncio.create_task(send_interrupt())

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_interrupt")

    await interrupt_task

    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']
    assert stream_chunks == [{'name': 'stdout', 'text': '0\n1\n2\n'}]

    assert chunks[-1]['msg']['msg_type'] == 'error'
    assert 'KeyboardInterrupt' in chunks[-1]['msg']['content']['ename']


async def test_kill(capsys):
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        import time
        for i in range(5):
            print(i)
            if i == 2:
                time.sleep(5)
        ```
    """)

    async def send_kill():
        while True:
            await asyncio.sleep(0.1)
            content = "".join([chunk['msg']['content']["text"]
                               for chunk in chunks
                               if chunk['msg']['msg_type'] == 'stream'])
            lines = content.split("\n")
            if len(lines) >= 2:
                break
        await run.signals["control"].kill.send_async(None)

    kill_task = asyncio.create_task(send_kill())

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_kill")

    await kill_task

    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']

    assert stream_chunks == [{'name': 'stdout', 'text': '0\n1\n2\n'}]

    kernel = await kernel_manager.get_kernel(None, "test_kill", None)
    is_alive = await kernel.is_alive() if kernel else False

    assert is_alive is False


async def test_custom_env():
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    custom_env = os.environ.copy()
    custom_env['CUSTOM_VAR'] = 'test_value'

    input_md = textwrap.dedent("""\
        ```python .eval
        import os
        print(os.environ.get('CUSTOM_VAR', 'Not found'))
        ```
    """)

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_custom_env", env=custom_env)

    assert len(chunks) > 0
    assert chunks[-1]['msg']['content']['text'].strip() == 'test_value'

    # Test that the custom environment doesn't persist for new kernels
    input_md = textwrap.dedent("""\
        ```python .eval
        import os
        print(os.environ.get('CUSTOM_VAR', 'Not found'))
        ```
    """)

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_custom_env_2")
    assert chunks[-1]['msg']['content']['text'].strip() == 'Not found'


async def test_bash_heredoc(capsys):
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent('''
        ```python .eval
        %%bash
        cat << 'EOF'
        content
        EOF
        ```
    ''')

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_bash_heredoc")

    # Get all output messages
    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']

    assert stream_chunks == [{'name': 'stdout', 'text': 'content\r\n'}]
