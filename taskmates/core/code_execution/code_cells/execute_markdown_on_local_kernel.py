import argparse
import asyncio
import os
import signal
import textwrap
from queue import Empty

import pytest
import sys
from jupyter_client import AsyncKernelManager, AsyncKernelClient
from nbformat import NotebookNode

from taskmates.core.code_execution.code_cells.parse_notebook import parse_notebook
from taskmates.logging import logger
from taskmates.signals.signals import Signals, SIGNALS

kernel_pool: dict[str, AsyncKernelManager] = {}


# Main execution function
async def execute_markdown_on_local_kernel(content, path: str = None, cwd: str = None):
    signals: Signals = SIGNALS.get()

    notebook: NotebookNode
    code_cells: list[NotebookNode]
    notebook, code_cells = parse_notebook(content)

    kernel_manager, kernel_client, setup_msgs = await get_or_start_kernel(cwd, path)

    msg_queue = asyncio.Queue()

    notebook_finished = False

    async def handle_shell_msg():
        while True:
            try:
                msg = await kernel_client.get_shell_msg(timeout=0.1)
                await msg_queue.put(msg)
            except Empty:
                pass

    async def handle_iopub_msg():
        while True:
            try:
                msg = await kernel_client.get_iopub_msg(timeout=0.1)
                await msg_queue.put(msg)
            except Empty:
                await msg_queue.put(None)

    shell_task = asyncio.create_task(handle_shell_msg())
    iopub_task = asyncio.create_task(handle_iopub_msg())

    async def interrupt_handler(sender):
        nonlocal notebook_finished
        notebook_finished = True
        await kernel_manager.interrupt_kernel()
        await signals.lifecycle.interrupted.send_async(None)

    async def kill_handler(sender):
        nonlocal notebook_finished
        nonlocal cell_finished
        logger.info("Killing kernel...")
        notebook_finished = True
        cell_finished = True
        await msg_queue.put(None)
        # TODO: note sure this works on windows
        await kernel_manager.signal_kernel(signal.SIGKILL)
        iopub_task.cancel()
        shell_task.cancel()
        await signals.lifecycle.killed.send_async(None)
        await kernel_manager.shutdown_kernel(now=True)

    with signals.control.interrupt.connected_to(interrupt_handler), \
            signals.control.kill.connected_to(kill_handler):

        try:
            for cell in code_cells:
                if notebook_finished:
                    break

                cell_finished = False

                source: str = cell.source
                # see https://stackoverflow.com/questions/57984815/whats-the-difference-between-bash-and-bang
                # in our case, `ack` is not working when called via %%bash
                if source.startswith("%%bash\n"):
                    # Remove the "%%bash\n" prefix
                    bash_content = source[7:]

                    # Escape newlines and single quotes
                    escaped_source = bash_content.replace("'", "'\\''").replace("\n", "\\n")

                    # Wrap the escaped content in $'...' syntax
                    escaped_source = f"$'{escaped_source}'"

                    source = f"!bash -c {escaped_source}"

                msg_id = kernel_client.execute(source)
                logger.debug("msg_id:", msg_id)

                while True:
                    msg = await msg_queue.get()
                    if msg is None:
                        if cell_finished:
                            break
                        continue
                    if msg['parent_header']['msg_id'] in setup_msgs and msg["msg_type"] != "error":
                        continue

                    if msg['parent_header']['msg_id'] != msg_id and msg["msg_type"] != "error":
                        continue

                    logger.debug(f"received msg: {msg['msg_type']}, msg_id={msg['parent_header']['msg_id']}")
                    logger.debug(f"    msg: {msg}")

                    if msg['msg_type'] == 'error':
                        notebook_finished = True

                    if msg['msg_type'] == 'execute_reply':
                        cell_finished = True
                        continue

                    # if msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                    #     break

                    if msg['msg_type'] not in ('stream', 'error', 'display_data', 'execute_result'):
                        continue

                    logger.debug("sending msg:", msg["msg_type"])
                    await signals.response.code_cell_output.send_async({
                        "msg_id": msg_id,
                        "cell_source": source,
                        "msg": msg
                    })
        finally:
            shell_task.cancel()
            iopub_task.cancel()
            kernel_client.stop_channels()


async def get_or_start_kernel(cwd, path):
    ignored = []
    is_new_kernel = True
    # Get or create a kernel manager for the given path
    if path in kernel_pool and (await kernel_pool[path].is_alive()):
        kernel_manager = kernel_pool[path]
        is_new_kernel = False
    else:
        kernel_manager = AsyncKernelManager(kernel_name='python3')
        await kernel_manager.start_kernel()
        kernel_pool[path] = kernel_manager
    kernel_client: AsyncKernelClient = kernel_manager.client()
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()
    if is_new_kernel:
        ignored.append(kernel_client.execute("%load_ext taskmates.magics.file_editing_magics"))
        ignored.append(kernel_client.execute("%matplotlib inline"))
        if cwd is not None:
            ignored.append(kernel_client.execute(f"%cd {cwd}"))
    return kernel_manager, kernel_client, ignored


async def main(argv=None):
    # Use argv if provided, else use sys.argv
    if argv is None:
        argv = sys.argv[1:]

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Execute markdown as Jupyter notebook.")
    parser.add_argument("--content", type=str, help="Markdown string to execute.")
    parser.add_argument("--path", type=str, help="Path associated with the kernel.")
    parser.add_argument("--cwd", type=str, help="Current working directory for the notebook execution.")
    args = parser.parse_args(argv)

    # Execute markdown
    await execute_markdown_on_local_kernel(content=args.content, path=args.path,
                                           cwd=args.cwd)


@pytest.mark.asyncio
async def test_code_cells_no_code():
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        # This is a markdown text

        This is a paragraph.
    """)
    await execute_markdown_on_local_kernel(input_md, path="test_no_code")
    assert chunks == []


@pytest.mark.asyncio
async def test_single_cell():
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + 3
        x
        ```
    """)
    await execute_markdown_on_local_kernel(input_md, path="test_simple_code")

    assert len(chunks) > 0

    assert len({chunk["msg_id"] for chunk in chunks}) == 1


@pytest.mark.asyncio
async def test_multiple_cells(tmp_path):
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

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

    await execute_markdown_on_local_kernel(content, path=str(tmp_path))

    assert len({chunk["msg_id"] for chunk in chunks}) == 2


@pytest.mark.asyncio
async def test_cell_error():
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

    input_md = textwrap.dedent("""\
        ```python .eval
        x = 2 + '3'
        ```

        ```python .eval
        print("It should not reach here!")
        ```

    """)
    await execute_markdown_on_local_kernel(input_md, path="test_error_code")

    assert 'error' in [chunk['msg']['msg_type'] for chunk in chunks]


@pytest.mark.asyncio
async def test_cwd(tmp_path):
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

    # Markdown content that gets the current working directory
    input_md = textwrap.dedent(f"""\
        ```python .eval
        import os
        print(os.getcwd())
        ```
    """)

    # Execute the markdown with cwd set to the temporary directory
    await execute_markdown_on_local_kernel(input_md, path="test_with_cwd", cwd=str(tmp_path))

    # Check if the output contains the expected directory path
    output_path = chunks[-1]['msg']['content']['text'].strip()
    expected_path = str(tmp_path)

    # Normalize paths for comparison
    assert os.path.normpath(output_path) == os.path.normpath(expected_path)


@pytest.mark.asyncio
async def test_change_cwd(tmp_path):
    signals = SIGNALS.get()
    chunks = []

    new_path = (tmp_path / "test_change_cwd")
    new_path.mkdir()

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

    # Markdown content that gets the current working directory
    input_md = textwrap.dedent(f"""\
        ```python .eval
        %cd {new_path}
        ```
    """)

    # Execute the markdown with cwd set to the temporary directory
    await execute_markdown_on_local_kernel(input_md, path="test_change_cwd", cwd=str(tmp_path))

    # Markdown content that gets the current working directory
    input_md = textwrap.dedent(f"""\
        ```python .eval
        import os
        print(os.getcwd())
        ```
    """)

    # Execute the markdown with cwd set to the temporary directory
    await execute_markdown_on_local_kernel(input_md, path="test_change_cwd", cwd=str(tmp_path))

    # Check if the output contains the expected directory path
    output_path = chunks[-1]['msg']['content']['text'].strip()
    expected_path = str(new_path)

    # Normalize paths for comparison
    assert os.path.normpath(output_path) == os.path.normpath(expected_path)


@pytest.mark.asyncio
async def test_interrupt(capsys):
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

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
        await signals.control.interrupt.send_async(None)

    interrupt_task = asyncio.create_task(send_interrupt())

    await execute_markdown_on_local_kernel(input_md, path="test_interrupt")

    await interrupt_task

    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']
    assert stream_chunks == [{'name': 'stdout', 'text': '0\n1\n2\n'}]

    assert chunks[-1]['msg']['msg_type'] == 'error'
    assert 'KeyboardInterrupt' in chunks[-1]['msg']['content']['ename']


@pytest.mark.asyncio
async def test_kill(capsys):
    signals = SIGNALS.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    signals.response.code_cell_output.connect(capture_chunk)

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
        await signals.control.kill.send_async(None)

    kill_task = asyncio.create_task(send_kill())

    await execute_markdown_on_local_kernel(input_md, path="test_kill")

    await kill_task

    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']

    assert stream_chunks == [{'name': 'stdout', 'text': '0\n1\n2\n'}]

    is_alive = await kernel_pool["test_kill"].is_alive()

    assert is_alive is False
