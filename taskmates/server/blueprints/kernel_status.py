from quart import Blueprint, jsonify
from taskmates.core.actions.code_execution.code_cells.kernel_manager import get_kernel_manager

kernel_status_bp = Blueprint('kernel_status', __name__)

@kernel_status_bp.route('/api/v1/kernel/status', methods=['GET'])
async def get_kernel_status():
    """Returns the current status of all kernels in the pool."""
    kernel_manager = get_kernel_manager()
    status = {}
    
    for key, kernel_manager_instance in kernel_manager._kernel_pool.items():
        cwd, markdown_path, env_hash = key
        is_alive = await kernel_manager_instance.is_alive()
        
        # Get the kernel client if it exists
        kernel_client = kernel_manager._client_pool.get(kernel_manager_instance)
        has_client = kernel_client is not None
        
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
            } if has_client else None
        }
    
    return jsonify({
        'total_kernels': len(kernel_manager._kernel_pool),
        'total_clients': len(kernel_manager._client_pool),
        'kernels': status
    })


import pytest
from quart.testing import QuartClient
from taskmates.server.server import app

@pytest.mark.asyncio
async def test_kernel_status_empty():
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
    from taskmates.core.actions.code_execution.code_cells.kernel_manager import get_kernel_manager
    
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
    finally:
        # Clean up
        await kernel_manager.cleanup_all()
