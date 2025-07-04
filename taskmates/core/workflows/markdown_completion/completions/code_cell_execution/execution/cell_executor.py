from nbformat import NotebookNode

from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.bash_script_handler import \
    BashScriptHandler
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.cell_status import \
    KernelCellTracker, CellExecutionStatus
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.message_handler import \
    MessageHandler
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.jupyter_notebook_logger import \
    jupyter_notebook_logger
from taskmates.core.workflows.signals.code_cell_output_signals import CodeCellOutputSignals


class CellExecutor:
    """Handles the execution of a single notebook cell."""

    def __init__(self, message_handler: MessageHandler, bash_script_handler: BashScriptHandler,
                 cell_tracker: KernelCellTracker, code_cell_output: CodeCellOutputSignals):
        self.message_handler = message_handler
        self.bash_script_handler = bash_script_handler
        self.cell_tracker = cell_tracker
        self.code_cell_output = code_cell_output

    async def execute_cell(self, cell: NotebookNode, cell_index: int, total_cells: int, setup_msgs: list[str]) -> bool:
        """
        Executes a single cell and returns True if execution should continue, False if it should stop.
        """
        if self.message_handler.notebook_finished:
            return False

        self.message_handler.reset_cell()

        source: str = cell.source
        jupyter_notebook_logger.debug(f"Executing cell {cell_index + 1}/{total_cells}")

        source = self.bash_script_handler.convert_if_bash(source)

        # Create a unique cell ID and register it with the tracker
        cell_id = f"cell_{cell_index}"
        self.cell_tracker.add_cell(cell_id, source)

        # Record the execution request
        msg_id = self.message_handler.kernel_client.execute(source, store_history=False)
        jupyter_notebook_logger.debug(f"Cell execution started: msg_id={msg_id}")

        # Record the sent message
        self.cell_tracker.record_sent_message(cell_id, {
            "msg_id": msg_id,
            "content": {"code": source}
        })

        while True:
            if self.message_handler._received_execute_reply and self.message_handler._received_idle_status:
                jupyter_notebook_logger.debug("Cell execution completed - both execute_reply and idle status received")
                self.message_handler.cell_finished = True

            if self.message_handler.cell_finished:
                break

            msg = await self.message_handler.get_message()
            if msg is None:
                jupyter_notebook_logger.debug("Received None message")
                continue

            jupyter_notebook_logger.debug(
                f"Processing message: {msg['msg_type']}, msg_id={msg['parent_header'].get('msg_id')}")
            jupyter_notebook_logger.debug(f"Message content: {msg}")

            msg_type = msg['msg_type']
            parent_msg_id = msg['parent_header'].get('msg_id')

            if parent_msg_id in setup_msgs and msg_type != "error":
                jupyter_notebook_logger.debug("Skipping setup message")
                continue

            if parent_msg_id != msg_id and msg_type != "error":
                jupyter_notebook_logger.debug(
                    f"Skipping message from different cell. Got {msg['parent_header'].get('msg_id')}, expecting {msg_id}")
                continue

            # Record received message
            self.cell_tracker.record_received_message(cell_id, msg)

            if msg_type == 'error':
                jupyter_notebook_logger.error(
                    f"Cell execution error: {msg['content'].get('ename')}: {msg['content'].get('evalue')}")
                self.message_handler.cell_finished = True
                self.message_handler.notebook_finished = True

            if msg_type == 'execute_reply':
                jupyter_notebook_logger.debug("Received execute_reply")
                self.message_handler._received_execute_reply = True
                continue

            if msg_type == 'status' and msg['content'].get('execution_state') == 'idle':
                jupyter_notebook_logger.debug("Received idle status")
                self.message_handler._received_idle_status = True
                continue

            if msg_type not in ('stream', 'error', 'display_data', 'execute_result'):
                jupyter_notebook_logger.debug(f"Skipping message type: {msg['msg_type']}")
                continue

            jupyter_notebook_logger.debug(f"Sending message to output streams: {msg['msg_type']}")
            await self.code_cell_output.code_cell_output.send_async({
                "msg_id": parent_msg_id,
                "cell_source": source,
                "msg": msg
            })

        return not self.message_handler.notebook_finished


async def test_cell_executor(tmp_path):
    from taskmates.core.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["code_cell_output"] = CodeCellOutputSignals()
    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    message_handler = MessageHandler(kernel_client, run.signals["status"])
    await message_handler.start()

    # Create cell tracker
    cell_tracker = KernelCellTracker()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), cell_tracker, run.signals["code_cell_output"])

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is True

    # Check output
    assert len(chunks) > 0
    assert any('Hello, World!' in str(chunk['msg']['content']) for chunk in chunks)

    # Check cell tracker
    assert len(cell_tracker.cells) == 1
    cell_status = cell_tracker.get_cell("cell_0")
    assert cell_status is not None
    assert cell_status.status == CellExecutionStatus.FINISHED
    assert len(cell_status.sent_messages) == 1
    assert len(cell_status.received_messages) > 0

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()


async def test_cell_executor_error(tmp_path):
    from taskmates.core.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["code_cell_output"] = CodeCellOutputSignals()
    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    message_handler = MessageHandler(kernel_client, run.signals["status"])
    await message_handler.start()

    # Create cell tracker
    cell_tracker = KernelCellTracker()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), cell_tracker, run.signals["code_cell_output"])

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is False

    # Check that we got an error message
    assert any(chunk['msg']['msg_type'] == 'error' for chunk in chunks)
    error_chunk = next(chunk for chunk in chunks if chunk['msg']['msg_type'] == 'error')
    assert 'ZeroDivisionError' in error_chunk['msg']['content']['ename']

    # Check cell tracker
    assert len(cell_tracker.cells) == 1
    cell_status = cell_tracker.get_cell("cell_0")
    assert cell_status is not None
    assert cell_status.status == CellExecutionStatus.ERROR
    assert 'ZeroDivisionError' in cell_status.error_info.get('ename', '')

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()


async def test_cell_executor_bash(tmp_path):
    from taskmates.core.workflow_engine.run import RUN
    from nbformat import NotebookNode

    run = RUN.get()
    chunks = []

    async def capture_chunk(chunk):
        chunks.append(chunk)

    run.signals["code_cell_output"] = CodeCellOutputSignals()
    run.signals["code_cell_output"].code_cell_output.connect(capture_chunk)

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

    message_handler = MessageHandler(kernel_client, run.signals["status"])
    await message_handler.start()

    # Create cell tracker
    cell_tracker = KernelCellTracker()

    # Create cell executor
    cell_executor = CellExecutor(message_handler, BashScriptHandler(), cell_tracker, run.signals["code_cell_output"])

    # Execute cell
    should_continue = await cell_executor.execute_cell(cell, 0, 1, [])
    assert should_continue is True

    # Check output
    assert len(chunks) > 0
    assert any('Hello from bash!' in str(chunk['msg']['content']) for chunk in chunks)

    # Check cell tracker
    assert len(cell_tracker.cells) == 1
    cell_status = cell_tracker.get_cell("cell_0")
    assert cell_status is not None
    assert cell_status.status == CellExecutionStatus.FINISHED
    assert len(cell_status.sent_messages) == 1
    assert len(cell_status.received_messages) > 0

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
    await kernel_manager.shutdown_kernel()
