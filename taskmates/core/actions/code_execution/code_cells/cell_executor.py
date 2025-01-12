from typing import Optional
from nbformat import NotebookNode

from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger
from taskmates.core.actions.code_execution.code_cells.message_handler import MessageHandler
from taskmates.core.actions.code_execution.code_cells.bash_script_handler import BashScriptHandler
from taskmates.workflow_engine.run import Run


class CellExecutor:
    """Handles the execution of a single notebook cell."""

    def __init__(self, message_handler: MessageHandler, bash_script_handler: BashScriptHandler, run: Run):
        self.message_handler = message_handler
        self.bash_script_handler = bash_script_handler
        self.run = run
        self.output_streams = run.signals["output_streams"]

    async def execute_cell(self, cell: NotebookNode, cell_index: int, total_cells: int, setup_msgs: list[str]) -> bool:
        """
        Executes a single cell and returns True if execution should continue, False if it should stop.
        """
        if self.message_handler.notebook_finished:
            return False

        self.message_handler.reset_cell()

        source: str = cell.source
        jupyter_notebook_logger.debug(f"Executing cell {cell_index + 1}/{total_cells}")
        jupyter_notebook_logger.debug(f"Cell source:\n{source}")

        source = self.bash_script_handler.convert_if_bash(source)

        msg_id = self.message_handler.kernel_client.execute(source)
        jupyter_notebook_logger.debug(f"Execution request sent with msg_id: {msg_id}")
        jupyter_notebook_logger.debug(f"Will wait for messages with parent_header.msg_id = {msg_id}")

        while True:
            if self.message_handler.cell_finished:
                break

            msg = await self.message_handler.get_message()
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
                jupyter_notebook_logger.debug(
                    f"Skipping message from different cell. Got {msg['parent_header'].get('msg_id')}, expecting {msg_id}")
                continue

            if msg['msg_type'] == 'error':
                jupyter_notebook_logger.error(f"Error in cell execution: {msg['content']}")
                self.message_handler.cell_finished = True
                self.message_handler.notebook_finished = True

            if msg['msg_type'] == 'execute_reply':
                jupyter_notebook_logger.debug("Cell execution completed")
                self.message_handler.cell_finished = True
                continue

            if msg['msg_type'] not in ('stream', 'error', 'display_data', 'execute_result'):
                jupyter_notebook_logger.debug(f"Skipping message type: {msg['msg_type']}")
                continue

            jupyter_notebook_logger.debug(f"Sending message to output streams: {msg['msg_type']}")
            jupyter_notebook_logger.debug(f"Message ID: {msg['parent_header'].get('msg_id')}")
            await self.output_streams.code_cell_output.send_async({
                "msg_id": msg['parent_header'].get('msg_id'),
                "cell_source": source,
                "msg": msg
            })

        return not self.message_handler.notebook_finished


async def test_cell_executor(tmp_path):
    from taskmates.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    # Create a simple cell
    cell = NotebookNode({
        'cell_type': 'code',
        'source': 'print("Hello, World!")',
        'metadata': {},
        'outputs': []
    })

    # Create message handler
    from jupyter_client import AsyncKernelManager
    kernel_manager = AsyncKernelManager(kernel_name='python3')
    await kernel_manager.start_kernel(cwd=str(tmp_path))
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()

    message_handler = MessageHandler(kernel_client, run)
    await message_handler.start()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), run)

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is True

    # Check output
    assert len(chunks) > 0
    assert any('Hello, World!' in str(chunk['msg']['content']) for chunk in chunks)

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()


async def test_cell_executor_error(tmp_path):
    from taskmates.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    # Create a cell with an error
    cell = NotebookNode({
        'cell_type': 'code',
        'source': '1/0',  # This will raise a ZeroDivisionError
        'metadata': {},
        'outputs': []
    })

    # Create message handler
    from jupyter_client import AsyncKernelManager
    kernel_manager = AsyncKernelManager(kernel_name='python3')
    await kernel_manager.start_kernel(cwd=str(tmp_path))
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()

    message_handler = MessageHandler(kernel_client, run)
    await message_handler.start()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), run)

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is False

    # Check that we got an error message
    assert any(chunk['msg']['msg_type'] == 'error' for chunk in chunks)
    error_chunk = next(chunk for chunk in chunks if chunk['msg']['msg_type'] == 'error')
    assert 'ZeroDivisionError' in error_chunk['msg']['content']['ename']

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()


async def test_cell_executor_bash(tmp_path):
    from taskmates.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["output_streams"].code_cell_output.connect(capture_chunk)

    # Create a bash cell
    cell = NotebookNode({
        'cell_type': 'code',
        'source': '%%bash\necho "Hello from bash!"',
        'metadata': {},
        'outputs': []
    })

    # Create message handler
    from jupyter_client import AsyncKernelManager
    kernel_manager = AsyncKernelManager(kernel_name='python3')
    await kernel_manager.start_kernel(cwd=str(tmp_path))
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()

    message_handler = MessageHandler(kernel_client, run)
    await message_handler.start()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), run)

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is True

    # Check output
    assert len(chunks) > 0
    assert any('Hello from bash!' in str(chunk['msg']['content']) for chunk in chunks)

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()
