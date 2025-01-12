from typing import Mapping, Tuple, List
from nbformat import NotebookNode

from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger
from taskmates.core.actions.code_execution.code_cells.kernel_manager import KernelManager, get_kernel_manager
from taskmates.core.actions.code_execution.code_cells.message_handler import MessageHandler
from taskmates.core.actions.code_execution.code_cells.bash_script_handler import BashScriptHandler
from taskmates.core.actions.code_execution.code_cells.cell_executor import CellExecutor
from taskmates.core.actions.code_execution.code_cells.signal_handler import SignalHandler
from taskmates.core.actions.code_execution.code_cells.parse_notebook import parse_notebook
from taskmates.core.actions.code_execution.code_cells.cell_status import KernelCellTracker
from taskmates.workflow_engine.run import Run


class MarkdownExecutor:
    """Coordinates the execution of markdown content as Jupyter notebook cells."""

    def __init__(self, run: Run, kernel_manager: KernelManager = None, bash_script_handler: BashScriptHandler = None):
        self.run = run
        self.kernel_manager = kernel_manager or get_kernel_manager()
        self.bash_script_handler = bash_script_handler or BashScriptHandler()
        self.message_handler = None
        self.signal_handler = None
        self.cell_executor = None

    async def setup(self, content: str, cwd: str = None, markdown_path: str = None, env: Mapping = None) -> Tuple[List[str], List[NotebookNode]]:
        """Sets up all components needed for execution."""
        jupyter_notebook_logger.debug(f"Setting up components for markdown_path={markdown_path}, cwd={cwd}")

        kernel_instance, kernel_client, setup_msgs = await self.kernel_manager.get_or_start_kernel(cwd, markdown_path, env)

        self.message_handler = MessageHandler(kernel_client, self.run)
        await self.message_handler.start()

        # Get or create cell tracker for this kernel
        key = (cwd, markdown_path, self.kernel_manager._get_env_hash(env))
        jupyter_notebook_logger.debug(f"Getting cell tracker for key: {key}")
        if key not in self.kernel_manager._cell_trackers:
            jupyter_notebook_logger.debug("Creating new cell tracker")
            self.kernel_manager._cell_trackers[key] = KernelCellTracker()
        cell_tracker = self.kernel_manager._cell_trackers[key]
        jupyter_notebook_logger.debug(f"Cell tracker has {len(cell_tracker.cells)} cells")

        self.signal_handler = SignalHandler(kernel_instance, self.message_handler, self.run)
        self.cell_executor = CellExecutor(self.message_handler, self.bash_script_handler, cell_tracker, self.run)

        # Parse notebook cells
        notebook, code_cells = parse_notebook(content)
        jupyter_notebook_logger.debug(f"Parsed {len(code_cells)} code cells")

        return setup_msgs, code_cells

    async def cleanup(self):
        """Cleans up all components."""
        jupyter_notebook_logger.debug("Cleaning up components")
        if self.message_handler:
            self.message_handler.cancel_tasks()

    async def execute(self, content: str, cwd: str = None, markdown_path: str = None, env: Mapping = None):
        """Executes markdown content as Jupyter notebook cells."""
        jupyter_notebook_logger.debug(f"Starting execution for markdown_path={markdown_path}, cwd={cwd}")

        setup_msgs, code_cells = await self.setup(content, cwd, markdown_path, env)

        with self.run.signals["control"].interrupt.connected_to(self.signal_handler.handle_interrupt), \
                self.run.signals["control"].kill.connected_to(self.signal_handler.handle_kill):

            try:
                for cell_index, cell in enumerate(code_cells):
                    should_continue = await self.cell_executor.execute_cell(cell, cell_index, len(code_cells), setup_msgs)
                    if not should_continue:
                        break
            finally:
                await self.cleanup()


import pytest
import asyncio
import textwrap
from pathlib import Path


@pytest.mark.asyncio
async def test_markdown_executor_simple_execution(tmp_path: Path):
    from taskmates.workflow_engine.run import RUN

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    executor = MarkdownExecutor(run)

    input_md = textwrap.dedent("""\
        ```python .eval
        print("Hello, World!")
        ```
    """)

    await executor.execute(input_md, cwd=str(tmp_path), markdown_path="test_simple")

    assert len(chunks) > 0
    assert any('Hello, World!' in str(chunk['msg']['content']) for chunk in chunks)


@pytest.mark.asyncio
async def test_markdown_executor_error_handling(tmp_path: Path):
    from taskmates.workflow_engine.run import RUN

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    executor = MarkdownExecutor(run)

    input_md = textwrap.dedent("""\
        ```python .eval
        1/0  # This will raise a ZeroDivisionError
        ```
    """)

    await executor.execute(input_md, cwd=str(tmp_path), markdown_path="test_error")

    assert any(chunk['msg']['msg_type'] == 'error' for chunk in chunks)
    error_chunk = next(chunk for chunk in chunks if chunk['msg']['msg_type'] == 'error')
    assert 'ZeroDivisionError' in error_chunk['msg']['content']['ename']


@pytest.mark.asyncio
async def test_markdown_executor_interrupt(tmp_path: Path):
    from taskmates.workflow_engine.run import RUN

    run = RUN.get()
    chunks = []
    status_signals = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    async def capture_status(signal):
        status_signals.append(signal)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)
    run.signals["status"].interrupted.connect(capture_status)

    executor = MarkdownExecutor(run)

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

    await executor.execute(input_md, cwd=str(tmp_path), markdown_path="test_interrupt")

    await interrupt_task

    stream_chunks = [chunk['msg']['content'] for chunk in chunks if chunk['msg']['msg_type'] == 'stream']
    assert stream_chunks == [{'name': 'stdout', 'text': '0\n1\n2\n'}]

    assert chunks[-1]['msg']['msg_type'] == 'error'
    assert 'KeyboardInterrupt' in chunks[-1]['msg']['content']['ename']
    assert len(status_signals) == 1
