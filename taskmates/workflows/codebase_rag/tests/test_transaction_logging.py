import pytest

import asyncio

from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.workflows.codebase_rag.tests.example_operation import example_operation, another_operation
from taskmates.core.workflow_engine.transaction_manager import TransactionManager, runtime

pytestmark = pytest.mark.no_cover


async def test_transaction_logging(tmp_path):
    """Test that transaction logging works correctly."""
    manager = TransactionManager(cache_dir=str(tmp_path / "cache"))

    with runtime.transaction_manager_context(manager):
        # Call operation through transaction manager
        result = await transactional(example_operation)(value=5)

        assert result == 10

        # Find the log file
        log_files = list(tmp_path.glob("cache/**/logs.txt"))
        assert len(log_files) == 1

        log_content = log_files[0].read_text()

        # Verify log contains expected messages
        assert "Starting operation with value: 5" in log_content
        assert "Processing value: 5" in log_content
        assert "Operation completed with result: 10" in log_content
        assert "INFO" in log_content
        assert "DEBUG" in log_content


async def test_transaction_logging_with_warning(tmp_path):
    """Test that warnings are logged correctly."""
    manager = TransactionManager(cache_dir=str(tmp_path / "cache"))

    with runtime.transaction_manager_context(manager):
        # Call operation with empty string to trigger warning
        result = await transactional(another_operation)(text="")

        assert result == ""

        # Find the log file
        log_files = list(tmp_path.glob("cache/**/logs.txt"))
        assert len(log_files) == 1

        log_content = log_files[0].read_text()

        # Verify warning is logged
        assert "Empty text provided" in log_content
        assert "WARNING" in log_content


async def test_multiple_operations_separate_logs(tmp_path):
    """Test that different operations get separate log files."""
    manager = TransactionManager(cache_dir=str(tmp_path / "cache"))

    with runtime.transaction_manager_context(manager):
        # Call two different operations
        result1 = await transactional(example_operation)(value=3)
        result2 = await transactional(another_operation)(text="hello")

        assert result1 == 6
        assert result2 == "HELLO"

        # Should have two separate log files
        log_files = list(tmp_path.glob("cache/**/logs.txt"))
        assert len(log_files) == 2

        # Read both log files
        log_contents = [f.read_text() for f in log_files]

        # One should contain example_operation logs
        assert any("Starting operation with value: 3" in content for content in log_contents)

        # Other should contain another_operation logs
        assert any("Processing text: hello" in content for content in log_contents)
