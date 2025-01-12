from typing import Mapping, Tuple, List, Dict, Any
from jupyter_client import AsyncKernelManager, AsyncKernelClient
from taskmates.lib.root_path.root_path import root_path
from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger


_KERNEL_MANAGER = None


def get_kernel_manager():
    global _KERNEL_MANAGER
    if _KERNEL_MANAGER is None:
        _KERNEL_MANAGER = KernelManager()
    return _KERNEL_MANAGER


class KernelManager:
    def __init__(self):
        # The key is now (cwd, markdown_path, env_hash)
        self._kernel_pool: dict[tuple[str | None, str | None, str | None], AsyncKernelManager] = {}
        self._client_pool: dict[AsyncKernelManager, AsyncKernelClient] = {}

    def _get_env_hash(self, env: Mapping | None) -> str | None:
        if env is None:
            return None
        # Convert env to a sorted list of tuples to ensure consistent hashing
        env_items = sorted((str(k), str(v)) for k, v in env.items())
        return str(hash(tuple(env_items)))

    async def get_or_start_kernel(self, cwd: str | None, markdown_path: str | None, env: Mapping | None = None) -> Tuple[AsyncKernelManager, AsyncKernelClient, List[str]]:
        ignored = []
        # Get or create a kernel manager for the given path
        env_hash = self._get_env_hash(env)
        key = (cwd, markdown_path, env_hash)
        if key in self._kernel_pool and (await self._kernel_pool[key].is_alive()):
            jupyter_notebook_logger.debug(f"Reusing kernel for {key}")
            is_new_kernel = False
            kernel_manager = self._kernel_pool[key]
            kernel_client = self._client_pool[kernel_manager]
        else:
            jupyter_notebook_logger.debug(f"Starting new kernel for {key}")
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
            self._kernel_pool[key] = kernel_manager

            kernel_client: AsyncKernelClient = kernel_manager.client()
            self._client_pool[kernel_manager] = kernel_client
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

    async def get_kernel(self, cwd: str | None, markdown_path: str | None, env: Mapping | None = None) -> AsyncKernelManager | None:
        env_hash = self._get_env_hash(env)
        return self._kernel_pool.get((cwd, markdown_path, env_hash))

    async def cleanup_kernel(self, kernel_manager: AsyncKernelManager) -> None:
        """Cleans up kernel resources."""
        jupyter_notebook_logger.debug("Cleaning up kernel resources: started")
        if kernel_manager in self._client_pool:
            kernel_client = self._client_pool[kernel_manager]
            kernel_client.stop_channels()
            del self._client_pool[kernel_manager]

        # Remove from kernel pool
        key_to_remove = None
        for key, km in self._kernel_pool.items():
            if km == kernel_manager:
                key_to_remove = key
                break
        if key_to_remove:
            del self._kernel_pool[key_to_remove]

        # Shutdown the kernel if it's still alive
        try:
            if await kernel_manager.is_alive():
                await kernel_manager.shutdown_kernel(now=True)
        except Exception as e:
            jupyter_notebook_logger.debug(f"Error shutting down kernel: {e}")

        jupyter_notebook_logger.debug("Cleaning up kernel resources: done")

    async def cleanup_all(self) -> None:
        """Cleans up all kernel resources."""
        jupyter_notebook_logger.debug("Cleaning up all kernel resources")
        for kernel_manager in list(self._client_pool.keys()):
            await self.cleanup_kernel(kernel_manager)


import pytest
import os
from pathlib import Path


@pytest.mark.asyncio
async def test_kernel_manager_lifecycle(tmp_path: Path):
    manager = KernelManager()

    # Start a kernel
    kernel_manager, kernel_client, ignored = await manager.get_or_start_kernel(str(tmp_path), "test_kernel")
    assert await kernel_manager.is_alive()
    assert await kernel_client.is_alive()

    # Test kernel execution
    kernel_client.execute("x = 42")
    assert await kernel_client.is_alive()

    # Test kernel reuse
    kernel_manager2, kernel_client2, ignored2 = await manager.get_or_start_kernel(str(tmp_path), "test_kernel")
    assert kernel_manager2 == kernel_manager
    assert kernel_client2 == kernel_client

    # Test cleanup
    await manager.cleanup_kernel(kernel_manager)
    assert not await kernel_client.is_alive()
    assert kernel_manager not in manager._client_pool


@pytest.mark.asyncio
async def test_kernel_manager_environment(tmp_path: Path):
    manager = KernelManager()

    # Create a custom environment
    custom_env = os.environ.copy()
    custom_env['CUSTOM_VAR'] = 'test_value'

    # Start a kernel with custom environment
    kernel_manager, kernel_client, ignored = await manager.get_or_start_kernel(
        str(tmp_path), "test_kernel", env=custom_env)

    # Start another kernel without custom environment
    kernel_manager2, kernel_client2, ignored2 = await manager.get_or_start_kernel(
        str(tmp_path), "test_kernel2")

    # They should be different kernels
    assert kernel_manager != kernel_manager2

    # Clean up
    await manager.cleanup_all()


@pytest.mark.asyncio
async def test_kernel_manager_cleanup_all(tmp_path: Path):
    manager = KernelManager()

    # Start multiple kernels
    km1, kc1, _ = await manager.get_or_start_kernel(str(tmp_path), "test_kernel1")
    km2, kc2, _ = await manager.get_or_start_kernel(str(tmp_path), "test_kernel2")

    assert len(manager._kernel_pool) == 2
    assert len(manager._client_pool) == 2

    # Clean up all
    await manager.cleanup_all()

    assert len(manager._kernel_pool) == 0
    assert len(manager._client_pool) == 0
    assert not await kc1.is_alive()
    assert not await kc2.is_alive()
