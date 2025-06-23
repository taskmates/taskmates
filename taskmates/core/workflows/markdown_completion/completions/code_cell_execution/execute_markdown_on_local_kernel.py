import argparse
import asyncio
import os
import sys
import textwrap
from typing import Mapping, Optional

import pytest
from typeguard import typechecked

from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.kernel_manager import \
    get_kernel_manager
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.markdown_executor import \
    MarkdownExecutor
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.jupyter_notebook_logger import \
    jupyter_notebook_logger

pytestmark = pytest.mark.slow


@typechecked
async def execute_markdown_on_local_kernel(content: str, markdown_path: Optional[str] = None, cwd: Optional[str] = None,
                                           env: Optional[Mapping] = None):
    """Main execution function that coordinates the execution of markdown content as Jupyter notebook cells."""
    run = RUN.get()
    executor = MarkdownExecutor(run.signals["control"], run.signals["status"], run.signals["code_cell_output"])
    await executor.execute(content, cwd=cwd, markdown_path=markdown_path, env=env)


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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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
        jupyter_notebook_logger.debug(f"Captured chunk: {chunk}")
        chunks.append(chunk)

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

    # Markdown content that gets the current working directory
    input_md = textwrap.dedent("""\
        ```python .eval
        import os
        print(os.getcwd())
        ```
    """)

    jupyter_notebook_logger.debug(f"Input markdown:\n{input_md}")
    jupyter_notebook_logger.debug(f"Expected cwd: {tmp_path}")

    # Execute the markdown with cwd set to the temporary directory
    await execute_markdown_on_local_kernel(input_md, markdown_path="test_with_cwd", cwd=str(tmp_path))

    jupyter_notebook_logger.debug(f"Captured chunks: {chunks}")

    # Check if we got any chunks
    assert len(chunks) > 0, "No output was captured"

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    kernel_manager = get_kernel_manager()
    kernel = await kernel_manager.get_kernel(None, "test_kill", None)
    is_alive = await kernel.is_alive() if kernel else False

    assert is_alive is False


async def test_custom_env():
    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent('''
        ```python .eval
        %%bash -s
        cat << 'EOF'
        content
        EOF
        ```
    ''')

    await execute_markdown_on_local_kernel(input_md, markdown_path="test_bash_heredoc")

    # Get all output messages
    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']

    assert stream_chunks == [{'name': 'stdout', 'text': 'content\n'}]
