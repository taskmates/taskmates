from typing import Mapping, Tuple, List
from jupyter_client import AsyncKernelManager, AsyncKernelClient
from taskmates.lib.root_path.root_path import root_path
from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger


class KernelManager:
    def __init__(self):
        self._kernel_pool: dict[tuple[str | None, str], AsyncKernelManager] = {}

    async def get_or_start_kernel(self, cwd: str | None, markdown_path: str | None, env: Mapping | None = None) -> Tuple[AsyncKernelManager, AsyncKernelClient, List[str]]:
        ignored = []
        # Get or create a kernel manager for the given path
        key = (cwd, markdown_path)
        if key in self._kernel_pool and (await self._kernel_pool[key].is_alive()):
            jupyter_notebook_logger.debug(f"Reusing kernel for {(cwd, markdown_path)}")
            is_new_kernel = False
            kernel_manager = self._kernel_pool[(cwd, markdown_path)]
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
            jupyter_notebook_logger.debug(f"Kernel started with id={kernel_manager.kernel_id}")
            self._kernel_pool[(cwd, markdown_path)] = kernel_manager

        kernel_client: AsyncKernelClient = kernel_manager.client()
        jupyter_notebook_logger.debug(f"Created kernel client for kernel_id={kernel_manager.kernel_id}")
        jupyter_notebook_logger.debug(f"Connection file: {kernel_client.connection_file}")
        jupyter_notebook_logger.debug(
            f"Channel ports - shell:{kernel_client.shell_port}, iopub:{kernel_client.iopub_port}, control:{kernel_client.control_port}")

        jupyter_notebook_logger.debug("Starting kernel channels")
        kernel_client.start_channels()
        jupyter_notebook_logger.debug("Channels started, waiting for kernel ready state")
        await kernel_client.wait_for_ready()
        jupyter_notebook_logger.debug(f"Kernel ready state confirmed. Kernel alive: {await kernel_manager.is_alive()}")

        if is_new_kernel:
            jupyter_notebook_logger.debug("Setting up new kernel")
            package_path = root_path()

            async def execute_setup_code(code):
                jupyter_notebook_logger.debug(f"Executing setup code:\n{code}")
                msg_id = kernel_client.execute(code)
                jupyter_notebook_logger.debug(f"Setup message sent with msg_id: {msg_id}")
                return msg_id

            jupyter_notebook_logger.debug("Starting kernel setup sequence")
            setup_msg_1 = await execute_setup_code(f"import sys; sys.path.append('{package_path}')")
            jupyter_notebook_logger.debug("sys.path setup completed")
            setup_msg_2 = await execute_setup_code("%load_ext taskmates.magics.file_editing_magics")
            jupyter_notebook_logger.debug("magics extension loaded")
            setup_msg_3 = await execute_setup_code("%matplotlib inline")
            jupyter_notebook_logger.debug("matplotlib setup completed")

            ignored = [setup_msg_1, setup_msg_2, setup_msg_3]
            jupyter_notebook_logger.debug(f"Setup complete. Ignored message IDs: {ignored}")

        return kernel_manager, kernel_client, ignored

    async def get_kernel(self, cwd: str | None, markdown_path: str | None) -> AsyncKernelManager | None:
        return self._kernel_pool.get((cwd, markdown_path))
