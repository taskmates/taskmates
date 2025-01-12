import asyncio
from queue import Empty
from typing import Optional

from jupyter_client import AsyncKernelClient
from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger
from taskmates.workflow_engine.run import Run


class MessageHandler:
    def __init__(self, kernel_client: AsyncKernelClient, run: Run):
        self.kernel_client = kernel_client
        self.run = run
        self.msg_queue = asyncio.Queue()
        self.notebook_finished = False
        self.cell_finished = False
        self._tasks = []

    async def start(self):
        self._tasks = [
            asyncio.create_task(self.handle_shell_msg()),
            asyncio.create_task(self.handle_iopub_msg()),
            asyncio.create_task(self.handle_control_msg())
        ]

    def cancel_tasks(self):
        for task in self._tasks:
            task.cancel()

    async def get_message(self) -> Optional[dict]:
        return await self.msg_queue.get()

    def reset_cell(self):
        self.cell_finished = False

    async def handle_shell_msg(self):
        jupyter_notebook_logger.debug("Starting shell message handler")
        while True:
            try:
                msg = await self.kernel_client.get_shell_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"Shell message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"Shell message parent_header: {msg['parent_header']}")
                jupyter_notebook_logger.debug(f"Shell message content: {msg['content']}")
                jupyter_notebook_logger.debug(f"Shell message metadata: {msg['metadata']}")
                await self.msg_queue.put(msg)
            except Empty:
                pass

    async def handle_iopub_msg(self):
        jupyter_notebook_logger.debug("Starting iopub message handler")
        while True:
            try:
                msg = await self.kernel_client.get_iopub_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"IOPub message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"IOPub message parent_header: {msg['parent_header']}")
                jupyter_notebook_logger.debug(f"IOPub message content: {msg['content']}")
                jupyter_notebook_logger.debug(f"IOPub message metadata: {msg['metadata']}")
                await self.msg_queue.put(msg)
            except Empty:
                pass

    async def handle_control_msg(self):
        jupyter_notebook_logger.debug("Starting control message handler")
        while True:
            try:
                msg = await self.kernel_client.get_control_msg(timeout=0.1)
                jupyter_notebook_logger.debug(f"Control message received: {msg['msg_type']}")
                jupyter_notebook_logger.debug(f"Control message parent_header: {msg['parent_header']}")
                jupyter_notebook_logger.debug(f"Control message content: {msg['content']}")
                jupyter_notebook_logger.debug(f"Control message metadata: {msg['metadata']}")

                if msg['msg_type'] == 'shutdown_reply':
                    jupyter_notebook_logger.debug("Kernel shutdown acknowledged")
                    self.notebook_finished = True
                    await self.run.signals["status"].killed.send_async(None)
                    break

                await self.msg_queue.put(msg)
            except Empty:
                pass
