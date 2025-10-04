import signal

from jupyter_client import AsyncKernelManager
from typeguard import typechecked

from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.execution.message_handler import \
    MessageHandler
from taskmates.core.workflows.markdown_completion.completions.code_cell_execution.jupyter_notebook_logger import \
    jupyter_notebook_logger
from taskmates.core.workflows.signals.status_signals import StatusSignals


@typechecked
class CodeCellExecutionSignalHandler:
    """Handles interrupt and kill signals for the kernel execution."""

    def __init__(self, kernel_manager: AsyncKernelManager, message_handler: MessageHandler, status: StatusSignals):
        self.kernel_manager = kernel_manager
        self.message_handler = message_handler
        self.status = status

    async def handle_interrupt(self, sender):
        """Handles the interrupt signal."""
        jupyter_notebook_logger.debug("Interrupt signal received")
        self.message_handler.notebook_finished = True
        await self.kernel_manager.interrupt_kernel()

        # TODO: the problem here is that this is not bidirectional
        # it's going child to parent
        await self.status.interrupted.send_async(None)

    async def handle_kill(self, sender):
        """Handles the kill signal."""
        jupyter_notebook_logger.debug("Kill signal received")
        self.message_handler.notebook_finished = True
        self.message_handler.cell_finished = True
        await self.message_handler.msg_queue.put(None)
        # TODO: note sure this works on windows
        await self.kernel_manager.signal_kernel(signal.SIGKILL)
        self.message_handler.cancel_tasks()
        await self.status.killed.send_async(None)
        await self.kernel_manager.shutdown_kernel(now=True)


async def test_signal_handler(tmp_path):
    status = StatusSignals(name="status")
    status_signals = []

    async def capture_status(signal):
        status_signals.append(signal)

    status.interrupted.connect(capture_status)
    status.killed.connect(capture_status)

    # Create kernel manager
    kernel_manager = AsyncKernelManager(kernel_name='python3')
    await kernel_manager.start_kernel(cwd=str(tmp_path))
    kernel_client = kernel_manager.client()
    kernel_client.start_channels()
    await kernel_client.wait_for_ready()

    # Create message handler
    message_handler = MessageHandler(kernel_client, status)
    await message_handler.start()

    # Create signal handler
    signal_handler = CodeCellExecutionSignalHandler(kernel_manager, message_handler, status)

    # Test interrupt
    await signal_handler.handle_interrupt(None)
    assert message_handler.notebook_finished is True
    assert len(status_signals) == 1
    assert status_signals[0] is None

    # Reset for kill test
    message_handler.notebook_finished = False
    status_signals.clear()

    # Test kill
    await signal_handler.handle_kill(None)
    assert message_handler.notebook_finished is True
    assert message_handler.cell_finished is True
    assert len(status_signals) == 1
    assert status_signals[0] is None

    # Verify kernel is shut down
    assert await kernel_manager.is_alive() is False

    # Clean up
    message_handler.cancel_tasks()
    kernel_client.stop_channels()
