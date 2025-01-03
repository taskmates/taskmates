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
from taskmates.workflows.contexts.context import Context

kernel_pool: dict[tuple[str | None, str], AsyncKernelManager] = {}

pytestmark = pytest.mark.slow


# Main execution function
async def execute_markdown_on_local_kernel(content, markdown_path: str = None, cwd: str = None, env: Mapping = None):
    run: Run[Context] = RUN.get()
    status = run.signals["status"]
    control = run.signals["control"]
    output_streams = run.signals["output_streams"]

    jupyter_notebook_logger.debug(f"Starting execution for markdown_path={markdown_path}, cwd={cwd}")

    notebook: NotebookNode
    code_cells: list[NotebookNode]
    notebook, code_cells = parse_notebook(content)

    jupyter_notebook_logger.debug(f"Parsed {len(code_cells)} code cells")

    kernel_manager, kernel_client, setup_msgs = await get_or_start_kernel(cwd, markdown_path, env)

    msg_queue = asyncio.Queue()

    notebook_finished = False

    async def handle_shell_msg():
        while True:
            try:
                msg = await kernel_client.get_shell_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"Shell message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"Shell message content: {msg}")
                await msg_queue.put(msg)
            except Empty:
                pass

    async def handle_iopub_msg():
        while True:
            try:
                msg = await kernel_client.get_iopub_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"IOPub message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"IOPub message content: {msg}")
                await msg_queue.put(msg)
            except Empty:
                pass

    async def handle_control_msg():
        while True:
            try:
                msg = await kernel_client.get_control_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"Control message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"Control message content: {msg}")

                if msg['msg_type'] == 'shutdown_reply':
                    jupyter_notebook_logger.debug("Kernel shutdown acknowledged")
                    nonlocal notebook_finished
                    notebook_finished = True
                    await status.killed.send_async(None)
                    break

                await msg_queue.put(msg)
            except Empty:
                pass

    shell_task = asyncio.create_task(handle_shell_msg())
    iopub_task = asyncio.create_task(handle_iopub_msg())
    control_task = asyncio.create_task(handle_control_msg())

    async def interrupt_handler(sender):
        nonlocal notebook_finished
        jupyter_notebook_logger.debug("Interrupt signal received")
        notebook_finished = True
        await kernel_manager.interrupt_kernel()
        await status.interrupted.send_async(None)

    async def kill_handler(sender):
        nonlocal notebook_finished
        nonlocal cell_finished
        jupyter_notebook_logger.debug("Kill signal received")
        notebook_finished = True
        cell_finished = True
        await msg_queue.put(None)
        # TODO: note sure this works on windows
        await kernel_manager.signal_kernel(signal.SIGKILL)
        iopub_task.cancel()
        shell_task.cancel()
        control_task.cancel()
        await status.killed.send_async(None)
        await kernel_manager.shutdown_kernel(now=True)

    with control.interrupt.connected_to(interrupt_handler), \
            control.kill.connected_to(kill_handler):

        try:
            for cell_index, cell in enumerate(code_cells):
                if notebook_finished:
                    break

                cell_finished = False

                source: str = cell.source
                jupyter_notebook_logger.debug(f"Executing cell {cell_index + 1}/{len(code_cells)}")
                jupyter_notebook_logger.debug(f"Cell source:\n{source}")

                # see https://stackoverflow.com/questions/57984815/whats-the-difference-between-bash-and-bang
                # in our case, `ack` is not working when called via %%bash
                if source.startswith("%%bash\n"):
                    # Remove the "%%bash\n" prefix
                    bash_content = source[7:]

                    # Create a temporary file with the bash script
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                        f.write(bash_content)
                        temp_path = f.name

                    # Make the script executable
                    os.chmod(temp_path, 0o755)

                    # Execute the script and clean up
                    source = f"!bash {temp_path}"
                    jupyter_notebook_logger.debug(f"Converted bash cell to: {source}")

                msg_id = kernel_client.execute(source)
                jupyter_notebook_logger.debug(f"Execution request sent with msg_id: {msg_id}")
                jupyter_notebook_logger.debug(f"Will wait for messages with parent_header.msg_id = {msg_id}")

                while True:
                    if cell_finished:
                        break
                    msg = await msg_queue.get()
                    if msg is None:
                        jupyter_notebook_logger.debug("Received None message")
                        continue

                    jupyter_notebook_logger.debug(
                        f"Processing message: {msg['msg_type']}, msg_id={msg['parent_header'].get('msg_id')}")
                    jupyter_notebook_logger.debug(f"Message content: {msg}")

                    if msg['parent_header'].get('msg_id') in setup_msgs and msg["msg_type"] != "error":
                        jupyter_notebook_logger.debug("Skipping setup message")
                        continue

                    if msg['parent_header'].get('msg_id') != msg_id and msg["msg_type"] != "error":
                        jupyter_notebook_logger.debug(f"Skipping message from different cell. Got {msg['parent_header'].get('msg_id')}, expecting {msg_id}")
                        continue

                    if msg['msg_type'] == 'error':
                        jupyter_notebook_logger.error(f"Error in cell execution: {msg['content']}")
                        cell_finished = True
                        notebook_finished = True

                    if msg['msg_type'] == 'execute_reply':
                        jupyter_notebook_logger.debug("Cell execution completed")
                        cell_finished = True
                        continue

                    if msg['msg_type'] not in ('stream', 'error', 'display_data', 'execute_result'):
                        jupyter_notebook_logger.debug(f"Skipping message type: {msg['msg_type']}")
                        continue

                    jupyter_notebook_logger.debug(f"Sending message to output streams: {msg['msg_type']}")
                    await output_streams.code_cell_output.send_async({
                        "msg_id": msg_id,
                        "cell_source": source,
                        "msg": msg
                    })
        finally:
            jupyter_notebook_logger.debug("Cleaning up kernel resources: started")
            shell_task.cancel()
            iopub_task.cancel()
            control_task.cancel()
            kernel_client.stop_channels()
            jupyter_notebook_logger.debug("Cleaning up kernel resources: done")


async def get_or_start_kernel(cwd, markdown_path, env=None):
    ignored = []
    # Get or create a kernel manager for the given path
    if markdown_path in kernel_pool and (await kernel_pool[(cwd, markdown_path)].is_alive()):
        jupyter_notebook_logger.debug(f"Reusing kernel for {(cwd, markdown_path)}")
        is_new_kernel = False
        kernel_manager = kernel_pool[(cwd, markdown_path)]
    else:
        jupyter_notebook_logger.debug(f"Starting new kernel for {(cwd, markdown_path)}")
        is_new_kernel = True
        kernel_manager = AsyncKernelManager(kernel_name='python3')
        kernel_args = {}
        if env is not None:
            kernel_args["env"] = env
        if cwd is not None:
            kernel_args["cwd"] = cwd

        jupyter_notebook_logger.debug(f"Kernel arguments: {kernel_args}")
        await kernel_manager.start_kernel(**kernel_args)
        # kernel_pool[(cwd, markdown_path)] = kernel_manager
        kernel_pool[(cwd, markdown_path)] = kernel_manager

    kernel_client: AsyncKernelClient = kernel_manager.client()
    jupyter_notebook_logger.debug("Starting kernel channels")
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()

    if is_new_kernel:
        jupyter_notebook_logger.debug("Setting up new kernel")
        package_path = root_path()
        setup_msg_1 = kernel_client.execute(f"import sys; sys.path.append('{package_path}')")
        jupyter_notebook_logger.debug(f"Setup message 1 sent with msg_id: {setup_msg_1}")
        setup_msg_2 = kernel_client.execute("%load_ext taskmates.magics.file_editing_magics")
        jupyter_notebook_logger.debug(f"Setup message 2 sent with msg_id: {setup_msg_2}")
        setup_msg_3 = kernel_client.execute("%matplotlib inline")
        jupyter_notebook_logger.debug(f"Setup message 3 sent with msg_id: {setup_msg_3}")
        ignored = [setup_msg_1, setup_msg_2, setup_msg_3]

    return kernel_manager, kernel_client, ignored


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

    is_alive = await kernel_pool[(None, "test_kill")].is_alive()

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

    assert len(chunks) > 1
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
