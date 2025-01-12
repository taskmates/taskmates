import pytest
from quart import Blueprint, jsonify

from taskmates.core.actions.code_execution.code_cells.kernel_manager import get_kernel_manager
from taskmates.core.actions.code_execution.code_cells.jupyter_notebook_logger import jupyter_notebook_logger

kernel_status_bp = Blueprint('kernel_status', __name__)


@kernel_status_bp.route('/api/v1/kernel/status', methods=['GET'])
async def get_kernel_status():
    """Returns the current status of all kernels in the pool."""
    kernel_manager = get_kernel_manager()
    status = {}

    jupyter_notebook_logger.debug(f"Total kernels: {len(kernel_manager._kernel_pool)}")
    jupyter_notebook_logger.debug(f"Total cell trackers: {len(kernel_manager._cell_trackers)}")
    jupyter_notebook_logger.debug(f"Cell tracker keys: {list(kernel_manager._cell_trackers.keys())}")

    for key, kernel_manager_instance in kernel_manager._kernel_pool.items():
        cwd, markdown_path, env_hash = key
        is_alive = await kernel_manager_instance.is_alive()

        jupyter_notebook_logger.debug(f"Processing kernel with key: {key}")
        jupyter_notebook_logger.debug(f"CWD: {cwd}, Markdown path: {markdown_path}, Env hash: {env_hash}")

        # Get the kernel client if it exists
        kernel_client = kernel_manager._client_pool.get(kernel_manager_instance)
        has_client = kernel_client is not None

        # Get the cell tracker if it exists
        cell_tracker = kernel_manager._cell_trackers.get(key)
        jupyter_notebook_logger.debug(f"Cell tracker found: {cell_tracker is not None}")
        if cell_tracker:
            jupyter_notebook_logger.debug(f"Cell tracker cells: {cell_tracker.cells}")

        status[str(key)] = {
            'cwd': cwd,
            'markdown_path': markdown_path,
            'env_hash': env_hash,
            'kernel_id': kernel_manager_instance.kernel_id,
            'is_alive': is_alive,
            'has_client': has_client,
            'connection_info': {
                'shell_port': kernel_client.shell_port if has_client else None,
                'iopub_port': kernel_client.iopub_port if has_client else None,
                'control_port': kernel_client.control_port if has_client else None,
            } if has_client else None,
            'cells': cell_tracker.to_dict() if cell_tracker else {'cells': {}, 'current_cell_id': None}
        }

    return jsonify({
        'total_kernels': len(kernel_manager._kernel_pool),
        'total_clients': len(kernel_manager._client_pool),
        'kernels': status
    })


@pytest.mark.asyncio
async def test_kernel_status_empty():
    from quart import Quart
    app = Quart(__name__)
    app.register_blueprint(kernel_status_bp)

    async with app.test_client() as client:
        response = await client.get('/api/v1/kernel/status')
        assert response.status_code == 200
        data = await response.get_json()
        assert 'total_kernels' in data
        assert 'total_clients' in data
        assert 'kernels' in data
        assert isinstance(data['kernels'], dict)


@pytest.mark.asyncio
async def test_kernel_status_with_kernel(tmp_path):
    from quart import Quart
    app = Quart(__name__)
    app.register_blueprint(kernel_status_bp)

    # Start a kernel
    kernel_manager = get_kernel_manager()
    kernel_instance, kernel_client, _ = await kernel_manager.get_or_start_kernel(
        str(tmp_path), "test_kernel"
    )

    try:
        async with app.test_client() as client:
            response = await client.get('/api/v1/kernel/status')
            assert response.status_code == 200
            data = await response.get_json()

            assert data['total_kernels'] == 1
            assert data['total_clients'] == 1

            # Get the first kernel status
            kernel_status = next(iter(data['kernels'].values()))
            assert kernel_status['is_alive'] is True
            assert kernel_status['has_client'] is True
            assert kernel_status['cwd'] == str(tmp_path)
            assert kernel_status['markdown_path'] == "test_kernel"
            assert kernel_status['connection_info'] is not None
            assert kernel_status['cells'] == {'cells': {}, 'current_cell_id': None}
    finally:
        # Clean up
        await kernel_manager.cleanup_all()


@pytest.mark.asyncio
async def test_kernel_status_with_executed_cell(tmp_path):
    from quart import Quart
    app = Quart(__name__)
    app.register_blueprint(kernel_status_bp)

    # Start a kernel and execute a cell
    from taskmates.core.actions.code_execution.code_cells.markdown_executor import MarkdownExecutor
    from taskmates.workflow_engine.run import RUN

    run = RUN.get()
    executor = MarkdownExecutor(run)

    input_md = """\
```python .eval
print("Hello, World!")
```
"""

    await executor.execute(input_md, cwd=str(tmp_path), markdown_path="test_kernel")

    try:
        async with app.test_client() as client:
            response = await client.get('/api/v1/kernel/status')
            assert response.status_code == 200
            data = await response.get_json()

            assert data['total_kernels'] == 1
            assert data['total_clients'] == 1

            # Get the first kernel status
            kernel_status = next(iter(data['kernels'].values()))
            assert kernel_status['is_alive'] is True
            assert kernel_status['has_client'] is True
            assert kernel_status['cwd'] == str(tmp_path)
            assert kernel_status['markdown_path'] == "test_kernel"
            assert kernel_status['connection_info'] is not None

            # Check cell execution information
            cells = kernel_status['cells']['cells']
            assert len(cells) == 1
            cell = next(iter(cells.values()))
            assert cell['status'] == 'finished'
            assert len(cell['sent_messages']) == 1
            assert len(cell['received_messages']) > 0
            assert cell['source'].strip() == 'print("Hello, World!")'
    finally:
        # Clean up
        kernel_manager = get_kernel_manager()
        await kernel_manager.cleanup_all()
