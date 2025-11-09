"""
Transaction Manager - Orchestrates cached execution of operations with logging and retry logic.

ARCHITECTURE OVERVIEW
=====================

This module provides a transactional execution framework for operations with automatic caching,
logging, and retry logic. The key components are:

1. **Transaction**: Represents a single execution of an operation
   - Created each time an operation is executed
   - Provides scoped logging to a transaction-specific log file
   - Stores reference to TransactionManager for nested operations
   - Automatically cleaned up when execution completes

2. **TransactionalOperation**: A reusable wrapper for an operation
   - Created by decorating a function with @transactional
   - Can be called multiple times, each call creates a new Transaction
   - Convenient for operations that need to be called repeatedly

3. **TransactionManager**: Orchestrates the execution framework
   - Manages cache storage and retrieval
   - Creates Transactions for each operation execution
   - Handles retry logic for failed operations
   - Supports parallel execution and queuing

4. **CurrentTransactionProxy** (accessed via `current_transaction`):
   - Provides access to the active Transaction from anywhere in the code
   - `current_transaction.logger` - transaction-scoped logging
   - `current_transaction.nest()` - execute nested operations with caching

USAGE PATTERNS
==============

Using the @transactional decorator (recommended):
    @transactional
    def my_operation(data):
        current_transaction.logger.info("Processing data")
        return process(data)

    # Simple call - uses auto-created default manager
    result = my_operation(data=value)

    # With custom manager via context
    with runtime.transaction_manager_context(custom_manager):
        result = my_operation(data=value)

Decorator with parameters:
    @transactional(max_retries=5, initial_delay=2.0, outcome="custom.name")
    def my_operation(data):
        return process(data)

Nested operations (from within an operation):
    def my_operation(data):
        # This operation runs in a Transaction
        current_transaction.logger.info("Processing data")

        # Call another operation, creating a nested Transaction
        result = current_transaction.nest(
            operation=other_operation
        )(data=data)
        return result

CACHING
=======

Each Transaction is identified by a cache key derived from:
- Operation name (module.function)
- Operation inputs (JSON-serialized and hashed)

Cached results are stored in: {cache_dir}/{operation_name}/{hash}/result.yml
Transaction logs are stored in: {cache_dir}/{operation_name}/{hash}/logs.txt
"""

import asyncio
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional, Callable, TypeVar

import pytest
import yaml
from blinker import Signal
from loguru import logger
from opentelemetry import trace
from ordered_set import OrderedSet
from pydantic import Field
from typeguard import typechecked

from taskmates.core.workflow_engine.composite_context_manager import CompositeContextManager
from taskmates.core.workflow_engine.generate_cache_key import generate_cache_key
from taskmates.core.workflow_engine.objective import ObjectiveKey, Objective
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflow_engine.transactions.no_op_logger import _noop_logger
from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.defaults.settings import Settings

Signal.set_class = OrderedSet

tracer = trace.get_tracer_provider().get_tracer(__name__)

WorkflowType = TypeVar('WorkflowType', bound=object)


@typechecked
class ExecutableTransaction(Transaction):
    """
    Represents a computation to be executed with caching and logging.

    A Transaction is an immutable value object that represents:
    - What operation to execute
    - What inputs to pass
    - Where the result will be cached (cache_key)
    - The execution context (manager, retry config)

    Transactions are created by TransactionalOperation and executed by TransactionManager.
    Each transaction corresponds to a unique cache location based on operation + inputs.

    Think of a Transaction as a promise/future - it represents a computation that will
    produce a result, which may already be cached or needs to be executed.
    """

    # Execution-specific fields (excluded from serialization)
    manager: 'TransactionManager' = Field(default=None, exclude=True)
    workflow_instance: Optional[WorkflowType] = Field(default=None, exclude=True)
    operation: Callable = Field(default=None, exclude=True)
    max_retries: int = Field(default=3, exclude=True)
    initial_delay: float = Field(default=1.0, exclude=True)

    def __init__(self,
                 manager: 'TransactionManager',
                 operation: Callable,
                 objective: Objective,
                 context: Optional[RunContext] = None,
                 workflow_instance: Optional[WorkflowType] = None,
                 max_retries: int = 3,
                 initial_delay: float = 1.0):
        # Initialize as a Transaction
        super().__init__(
            objective=objective,
            context=context,
            manager=manager,
            workflow_instance=workflow_instance,
            operation=operation,
            max_retries=max_retries,
            initial_delay=initial_delay
        )

    async def __call__(self) -> Any:
        """Execute the operation via manager.execute with caching and retry logic."""
        return await self.manager.execute(
            transaction=self,
            operation=self.operation,
            max_retries=self.max_retries,
            initial_delay=self.initial_delay
        )


class TransactionalOperation:
    """
    Wrapper for transactional operations.

    Created by the @transactional decorator to wrap both workflow methods and standalone functions.
    """

    def __init__(self,
                 operation: Callable,
                 outcome: Optional[str] = None,
                 max_retries: int = 3,
                 initial_delay: float = 1.0
                 ):
        self.operation = operation
        self._instance = None  # Will be set by __get__ for methods

        # Compute outcome from the operation itself
        if outcome is not None:
            self.outcome = outcome
        else:
            self.outcome = f"{operation.__module__}.{operation.__qualname__}"

        # Retry configuration
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    async def __call__(self, **kwargs) -> Any:
        transaction_manager = runtime.transaction_manager()

        # Use context from self if provided, otherwise from active transaction, otherwise from Settings
        context = Settings().get()

        # Create objective from inputs
        objective = Objective(
            key=ObjectiveKey(
                outcome=self.outcome,
                inputs=kwargs
            )
        )

        # Create executable transaction
        transaction = ExecutableTransaction(
            manager=transaction_manager,
            context=context,
            operation=self.operation,
            objective=objective,
            workflow_instance=self._instance,
            max_retries=self.max_retries,
            initial_delay=self.initial_delay
        )

        return await transaction()

    def __get__(self, instance, owner):
        """Support instance method binding for workflow methods."""
        if instance is None:
            return self
        # Create a copy with the instance bound
        bound = TransactionalOperation(
            operation=self.operation,
            outcome=self.outcome
        )
        bound._instance = instance
        return bound


class TransactionManager:
    """
    Manages transactional execution of operations with caching, logging, and retry logic.

    The TransactionManager orchestrates the execution of operations by:
    - Creating a Transaction for each operation execution
    - Managing cache storage and retrieval
    - Handling retry logic for failed operations
    - Supporting parallel execution of multiple operations
    - Providing queuing mechanisms for batch processing

    Each operation execution happens within a Transaction that provides:
    - Scoped logging to a transaction-specific log file
    - Access to nested operation calls via current_transaction.nest()
    - Automatic cleanup of resources

    Key concepts:
    - **Transaction**: A single execution of an operation (created per call)
    - **TransactionalOperation**: A reusable wrapper that executes an operation transactionally
    - **Cache Key**: Derived from operation name + inputs, identifies cached results
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the transaction manager.

        Args:
            cache_dir: Directory for caching results. If None, uses in-memory cache.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache when cache_dir is None
        self._memory_cache: Dict[str, Any] = {}

    def build_executable_transaction(self,
                                     operation: Callable,
                                     outcome: str,
                                     context: Optional[Dict] = None,
                                     result_format: Optional[Dict] = None,
                                     inputs: Optional[Dict[str, Any]] = None,
                                     workflow_instance: Optional[WorkflowType] = None) -> ExecutableTransaction:
        """Build an executable transaction for both workflow methods and standalone functions."""

        # Use context in priority order: parameter > Settings
        if context is not None:
            tx_context = context
        else:
            tx_context = Settings().get()

        objective = Objective(
            key=ObjectiveKey(
                outcome=outcome,
                inputs=inputs
            ),
            result_format=result_format or {'format': 'completion', 'interactive': False}
        )

        return ExecutableTransaction(
            manager=self,
            objective=objective,
            context=tx_context,
            workflow_instance=workflow_instance,
            operation=operation
        )

    def _get_cache_path(self, cache_key: str) -> Optional[Path]:
        """Get the cache path for a given key."""
        if not self.cache_dir:
            return None
        return self.cache_dir / cache_key / "result.yml"

    def _get_log_path(self, cache_key: str) -> Optional[Path]:
        """Get the log path for a given key."""
        if not self.cache_dir:
            return None
        return self.cache_dir / cache_key / "logs.txt"

    def get_cached_result(self, outcome: str, inputs: Dict[str, Any]) -> Optional[Any]:
        cache_key = generate_cache_key(outcome, inputs)

        # Try in-memory cache first
        if self.cache_dir is None:
            return None
            # return self._memory_cache.get(cache_key)

        # Try file-based cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path and cache_path.exists():
            with open(cache_path, 'r') as f:
                return yaml.safe_load(f)

        return None

    def set_cached_result(self, outcome: str, inputs: Dict[str, Any], result: Any) -> None:
        cache_key = generate_cache_key(outcome, inputs)

        # Store in memory cache
        if self.cache_dir is None:
            # self._memory_cache[cache_key] = result
            return

        # Store in file-based cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Store operation info
            operation_file = cache_path.parent / "operation.yml"
            with open(operation_file, 'w') as f:
                yaml.dump({'operation': outcome}, f, default_flow_style=False)

            # Store inputs
            inputs_file = cache_path.parent / "inputs.yml"
            with open(inputs_file, 'w') as f:
                yaml.dump(inputs, f, default_flow_style=False)

            # Store result
            with open(cache_path, 'w') as f:
                yaml.dump(result, f, default_flow_style=False)

    def has_cached_result(self, outcome: str, inputs: Dict[str, Any]) -> bool:
        cache_key = generate_cache_key(outcome, inputs)

        # Check in-memory cache
        if self.cache_dir is None:
            return False
            # return cache_key in self._memory_cache

        # Check file-based cache
        result_file = self.cache_dir / cache_key / "result.yml"
        return result_file.exists()

    def queue(self, operation: Callable, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Queue an operation for processing by creating cache entry without result.

        Args:
            operation: Callable to queue
            inputs: Dictionary of input parameters

        Returns:
            Handle dict containing operation, inputs, and cache_key for later retrieval
        """
        if not self.cache_dir:
            raise RuntimeError("Cannot queue operations without cache_dir")

        operation_name = f"{operation.__module__}.{operation.__name__}"
        cache_key = generate_cache_key(operation_name, inputs)
        cache_dir = self.cache_dir / cache_key
        cache_dir.mkdir(parents=True, exist_ok=True)

        operation_file = cache_dir / "operation.yml"
        inputs_file = cache_dir / "inputs.yml"

        with open(operation_file, 'w') as f:
            yaml.dump({'operation': operation_name}, f, default_flow_style=False)

        with open(inputs_file, 'w') as f:
            yaml.dump(inputs, f, default_flow_style=False)

        logger.info(f"Queued operation {operation_name} with cache key {cache_key}")

        return {
            'operation': operation,
            'operation_name': operation_name,
            'inputs': inputs,
            'cache_key': cache_key
        }

    def is_queued(self, outcome: str, inputs: Dict[str, Any]) -> bool:
        """
        Check if an operation is queued (has inputs/operation but no result).

        Args:
            outcome: Name of the operation
            inputs: Dictionary of input parameters

        Returns:
            True if operation is queued, False otherwise
        """
        if not self.cache_dir:
            return False

        cache_key = generate_cache_key(outcome, inputs)
        cache_dir = self.cache_dir / cache_key

        operation_file = cache_dir / "operation.yml"
        result_file = cache_dir / "result.yml"

        return operation_file.exists() and not result_file.exists()

    def get_result(self, handle: Dict[str, Any]) -> Any:
        """
        Get the result for a queued operation using its handle.

        Args:
            handle: Handle dict returned from queue()

        Returns:
            Result of the operation (from cache)

        Raises:
            ValueError: If operation hasn't been processed yet
        """
        operation_name = handle['operation_name']
        inputs = handle['inputs']

        result = self.get_cached_result(operation_name, inputs)
        if result is None:
            raise ValueError(
                f"Operation {operation_name} [{handle['cache_key']}] has not been processed yet. "
                f"Call process_queued() first."
            )

        return result

    def get_results(self, handles: list[Dict[str, Any]]) -> list[Any]:
        """
        Get results for multiple queued operations.

        Args:
            handles: List of handle dicts returned from queue()

        Returns:
            List of results in the same order as handles
        """
        return [self.get_result(handle) for handle in handles]

    async def process_queued(self, handles: list[Dict[str, Any]], max_retries: int = 3,
                             initial_delay: float = 1.0) -> None:
        """
        Process queued operations sequentially.

        Args:
            handles: List of handle dicts returned from queue()
            max_retries: Maximum number of retry attempts per operation
            initial_delay: Initial delay in seconds before first retry
        """
        for handle in handles:
            operation = handle['operation']
            inputs = handle['inputs']

            # Skip if already cached
            if self.has_cached_result(handle['operation_name'], inputs):
                logger.info(f"Skipping {handle['operation_name']} [{handle['cache_key']}] - already cached")
                continue

            # Execute the operation
            transactional_op = TransactionalOperation(
                operation=operation,
                outcome=None,
                max_retries=max_retries,
                initial_delay=initial_delay
            )
            await transactional_op(**inputs)

    async def map_parallel(self, operation: Callable, inputs_list: list[Dict[str, Any]],
                           max_workers: Optional[int] = 1, max_retries: int = 3,
                           initial_delay: float = 1.0) -> list[Any]:
        """
        Execute an operation in parallel over multiple inputs.

        This is a convenience method that combines queue() + parallel processing + get_results().

        Args:
            operation: Callable to execute (can be a TransactionalOperation or plain function)
            inputs_list: List of input dicts, one per operation call
            max_workers: Maximum number of parallel workers (default: 1)
            max_retries: Maximum number of retry attempts per operation
            initial_delay: Initial delay in seconds before first retry

        Returns:
            List of results in the same order as inputs_list
        """
        # Handle TransactionalOperation - extract the underlying operation
        if isinstance(operation, TransactionalOperation):
            actual_operation = operation.operation
            outcome = operation.outcome
        else:
            actual_operation = operation
            outcome = None

        if not self.cache_dir:
            # Without caching, just execute sequentially
            results = []
            transactional_op = TransactionalOperation(
                operation=actual_operation,
                outcome=outcome,
                max_retries=max_retries,
                initial_delay=initial_delay
            )
            for inputs in inputs_list:
                result = await transactional_op(**inputs)
                results.append(result)
            return results

        # Queue all operations and collect handles
        handles = [self.queue(actual_operation, inputs) for inputs in inputs_list]

        # Filter to only unprocessed operations
        unprocessed_handles = [
            handle for handle in handles
            if not self.has_cached_result(handle['operation_name'], handle['inputs'])
        ]

        if unprocessed_handles:
            logger.info(f"Processing {len(unprocessed_handles)} operations in parallel "
                        f"({len(handles) - len(unprocessed_handles)} already cached)")

            # Process in parallel using asyncio.gather
            if max_workers is None or max_workers == 1:
                # Sequential execution
                for handle in unprocessed_handles:
                    transactional_op = TransactionalOperation(
                        operation=handle['operation'],
                        outcome=None,
                        max_retries=max_retries,
                        initial_delay=initial_delay
                    )
                    await transactional_op(**handle['inputs'])
            else:
                # Parallel execution with semaphore
                semaphore = asyncio.Semaphore(max_workers)

                async def process_with_semaphore(handle):
                    async with semaphore:
                        transactional_op = TransactionalOperation(
                            operation=handle['operation'],
                            outcome=None,
                            max_retries=max_retries,
                            initial_delay=initial_delay
                        )
                        return await transactional_op(**handle['inputs'])

                await asyncio.gather(*[process_with_semaphore(handle) for handle in unprocessed_handles])
        else:
            logger.info(f"All {len(handles)} operations already cached")

        # Return results in original order
        return self.get_results(handles)

    async def execute(
            self,
            transaction: Transaction,
            operation: Callable,
            max_retries: int = 3,
            initial_delay: float = 1.0
    ) -> Any:
        """
        Execute a transaction with caching, retry logic, and isolated logging.

        Args:
            transaction: Transaction to execute
            operation: The actual operation to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry

        Returns:
            Result from executing the transaction
        """

        outcome = transaction.objective.key['outcome']
        inputs = transaction.objective.key['inputs']

        # Check cache first
        cached_result = self.get_cached_result(outcome, inputs)
        if cached_result is not None:
            logger.info(f"Cache HIT for {outcome}")
            return cached_result

        logger.info(f"Cache MISS for {outcome} - executing operation")

        # Setup transaction-scoped logging
        cache_key = generate_cache_key(outcome, inputs)
        log_path = self._get_log_path(cache_key)

        sink_id = None
        transaction_logger = logger
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            transaction_logger = logger.bind(transaction_id=cache_key)
            sink_id = transaction_logger.add(
                str(log_path),
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                filter=lambda record: record["extra"].get("transaction_id") == cache_key,
                level="DEBUG"
            )

        # Set logger on transaction
        transaction.logger = transaction_logger

        # Set as current transaction
        token = runtime.set(transaction)

        try:
            async with transaction.async_transaction_context():
                last_exception = None
                delay = initial_delay

                for attempt in range(max_retries):
                    try:
                        # Handle workflow instance if present
                        if hasattr(transaction, 'workflow_instance') and transaction.workflow_instance is not None:
                            result = await operation(transaction.workflow_instance, **inputs)
                        else:
                            result = await operation(**inputs)

                        # Cache the result
                        self.set_cached_result(outcome, inputs, result)
                        logger.info(f"Cached result for {outcome}")

                        return result

                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_retries} failed for {outcome}: {e}. "
                                f"Retrying in {delay:.1f}s..."
                            )
                            await asyncio.sleep(delay)
                            delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"All {max_retries} attempts failed for {outcome}: {e}")

                # If we get here, all retries failed
                raise last_exception

        finally:
            runtime.reset(token)
            if sink_id is not None:
                logger.remove(sink_id)


class Runtime:
    """
    Proxy that provides access to the current transaction.

    This allows operations to:
    - Access transaction-scoped logging via `current_transaction.logger`
    - Execute nested operations with caching via `current_transaction.nest()`

    The proxy uses a context variable to track the active transaction, allowing
    nested transactions to work correctly even in concurrent execution scenarios.
    """

    def set(self, transaction: Transaction):
        return _current_transaction_context_var.set(transaction)

    def reset(self, token):
        return _current_transaction_context_var.reset(token)

    @property
    def transaction(self) -> Optional[Transaction]:
        return _current_transaction_context_var.get()

    @property
    def logger(self):
        """Get the logger for the current transaction, or a no-op logger if none exists."""
        ctx = _current_transaction_context_var.get()
        return ctx.logger if ctx else _noop_logger

    def map_parallel(self, operation: Callable, inputs_list: list[Dict[str, Any]],
                     max_workers: Optional[int] = None, max_retries: int = 3,
                     initial_delay: float = 1.0) -> list[Any]:
        """
        Execute an operation in parallel over multiple inputs within the current transaction.

        Args:
            operation: Callable to execute
            inputs_list: List of input dicts, one per operation call
            max_workers: Maximum number of parallel workers
            max_retries: Maximum number of retry attempts per operation
            initial_delay: Initial delay in seconds before first retry

        Returns:
            List of results in the same order as inputs_list

        Raises:
            RuntimeError: If called outside of a transaction context
        """
        ctx = _current_transaction_context_var.get()
        if ctx is None:
            raise RuntimeError("map_parallel() called outside of transaction context")

        return ctx.manager.map_parallel(operation, inputs_list, max_workers, max_retries, initial_delay)

    def transaction_manager(self) -> TransactionManager:
        """
        Get the active transaction manager from context, or fall back to default.

        Priority order:
        1. Manager from runtime.transaction_manager_context (if in one)
        2. Manager from current transaction (if in one)
        3. Global default manager

        Returns:
            The active TransactionManager instance
        """
        manager = _current_transaction_manager_context_var.get()
        if manager is not None:
            return manager

        return get_default_transaction_manager()

    def transaction_manager_context(self, manager: TransactionManager):
        """
        Context manager for using a specific TransactionManager.

        Example:
            custom_manager = TransactionManager(cache_dir="/custom/path")

            with runtime.transaction_manager_context(custom_manager):
                result = await my_transactional_operation(data)
        """

        @contextmanager
        def _context():
            token = _current_transaction_manager_context_var.set(manager)
            try:
                yield manager
            finally:
                _current_transaction_manager_context_var.reset(token)

        return _context()


def get_default_transaction_manager() -> TransactionManager:
    """
    Get or create the global default transaction manager.

    The default manager uses in-memory caching (cache_dir=None).
    For persistent caching, create a custom TransactionManager with a cache_dir.

    Returns:
        The global default TransactionManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = TransactionManager(cache_dir=None)
    return _default_manager


_current_transaction_context_var: ContextVar[Optional[Transaction]] = ContextVar('current_transaction', default=None)
runtime = Runtime()

# Global default manager
_default_manager: Optional[TransactionManager] = None
_current_transaction_manager_context_var: ContextVar[Optional[TransactionManager]] = ContextVar('transaction_manager',
                                                                                                default=None)


# Tests


class MockDaemon(CompositeContextManager):  # type: ignore[misc, type-arg]
    pass


class MockDaemon1(CompositeContextManager):  # type: ignore[misc, type-arg]
    pass


class MockDaemon2(CompositeContextManager):  # type: ignore[misc, type-arg]
    pass


@pytest.fixture
def test_context() -> RunContext:
    return RunContext(
        runner_environment={
            "taskmates_dirs": [],
            "markdown_path": "test.md",
            "cwd": "/tmp"
        },
        run_opts={
            "model": "test",
            "max_steps": 10
        }
    )


def test_objective_key():
    # Test basic key creation
    key1 = ObjectiveKey(outcome="test", inputs={"key": "value"})
    key2 = ObjectiveKey(outcome="test", inputs={"key": "value"})
    key3 = ObjectiveKey(outcome="test", inputs={"key": "different"})

    # Test equality
    assert key1 == key2
    assert key1 != key3

    # Test hashing
    d = {key1: "value1", key3: "value3"}
    assert d[key2] == "value1"  # key2 should hash to the same value as key1

    # Test dictionary interface
    assert key1["outcome"] == "test"
    assert key1["inputs"] == {"key": "value"}


# def test_objective_with_key():
#     # Test that Objective properly uses ObjectiveKey
#     key = ObjectiveKey(outcome="test", inputs={"key": "value"})
#     obj = Objective(key=key)
#
#     # Test that the key values are preserved
#     assert obj.key == key  # Check equality instead of identity
#     assert obj.key['outcome'] == "test"
#     assert obj.key['inputs'] == {"key": "value"}
#
#     # Test sub_objectives with keys
#     sub_key = ObjectiveKey(outcome="sub_test", inputs={"arg": "value"})
#     sub_obj = obj.get_or_create_sub_objective(sub_key['outcome'], sub_key['inputs'])
#     assert isinstance(sub_obj, Objective)
#
#     # Test that the same key returns the same sub_objective
#     sub_obj2 = obj.get_or_create_sub_objective(sub_key['outcome'], sub_key['inputs'])
#     assert sub_obj2 is sub_obj  # This should still be the same instance


# def test_run_serialization(context: RunContext) -> None:
#     # Create a simple objective with ObjectiveKey
#     key = ObjectiveKey(outcome="test_outcome", inputs={"key": "value"})
#     objective = Objective(key=key)
#
#     # Create signals
#     emits = {"test_group": BaseSignals(name="BaseSignals")}
#     emits["test_group"].namespace.signal("test_signal")
#     consumes = {"test_group": BaseSignals(name="BaseSignals")}
#     consumes["test_group"].namespace.signal("test_signal")
#
#     # Create a Run instance
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits=emits,
#         consumes=consumes,
#         state={"state_key": "state_value"},
#         daemons={"test_daemon": MockDaemon()}
#     )
#
#     # Serialize
#     json_str = run.model_dump_json()
#
#     # Deserialize
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     # Verify the deserialized run
#     assert deserialized_run.objective.key == run.objective.key
#     assert deserialized_run.execution_context.state == run.execution_context.state
#     assert isinstance(list(deserialized_run.daemons.values())[0], MockDaemon)
#     assert "test_signal" in list(deserialized_run.execution_context.emits.values())[0].namespace
#     assert "test_signal" in list(deserialized_run.execution_context.consumes.values())[0].namespace


# def test_run_serialization_with_complex_data(context: RunContext) -> None:
#     key = ObjectiveKey(
#         outcome="complex_test",
#         inputs={
#             "nested": {"a": 1, "b": [1, 2, 3]},
#             "list": [1, "two", {"three": 3}]
#         }
#     )
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits={},
#         consumes={},
#         state={"complex": {"nested": True}},
#         daemons={}
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert deserialized_run.objective.key == run.objective.key
#     assert deserialized_run.execution_context.state == run.execution_context.state


# def test_run_serialization_with_multiple_daemons(context: RunContext) -> None:
#     key = ObjectiveKey(outcome="multi_daemon_test")
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={
#             "daemon1": MockDaemon1(),
#             "daemon2": MockDaemon2()
#         }
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert isinstance(deserialized_run.daemons["daemon1"], MockDaemon1)
#     assert isinstance(deserialized_run.daemons["daemon2"], MockDaemon2)


# def test_run_serialization_with_multiple_signal_groups(context: RunContext) -> None:
#     emits = {
#         "group1": BaseSignals(name="BaseSignals"),
#         "group2": BaseSignals(name="BaseSignals")
#     }
#     consumes = {
#         "group1": BaseSignals(name="BaseSignals"),
#         "group2": BaseSignals(name="BaseSignals")
#     }
#
#     emits["group1"].namespace.signal("signal1")
#     emits["group1"].namespace.signal("signal2")
#     emits["group2"].namespace.signal("signal3")
#
#     consumes["group1"].namespace.signal("signal1")
#     consumes["group1"].namespace.signal("signal2")
#     consumes["group2"].namespace.signal("signal3")
#
#     key = ObjectiveKey(outcome="multi_signal_test")
#     objective = Objective(key=key)
#
#     run: Transaction = Transaction(
#         objective=objective,
#         context=context,
#         emits=emits,
#         consumes=consumes,
#         state={},
#         daemons={}
#     )
#
#     json_str = run.model_dump_json()
#     deserialized_run = Transaction.model_validate_json(json_str)
#
#     assert "signal1" in deserialized_run.execution_context.emits["group1"].namespace
#     assert "signal2" in deserialized_run.execution_context.emits["group1"].namespace
#     assert "signal3" in deserialized_run.execution_context.emits["group2"].namespace
#     assert "signal1" in deserialized_run.execution_context.consumes["group1"].namespace
#     assert "signal2" in deserialized_run.execution_context.consumes["group1"].namespace
#     assert "signal3" in deserialized_run.execution_context.consumes["group2"].namespace


# def test_objective_initialization():
#     # Test initialization with ObjectiveKey
#     obj = Objective(key=ObjectiveKey(outcome="test", inputs={"key": "value"}))
#     assert obj.key['outcome'] == "test"
#     assert obj.key['inputs'] == {"key": "value"}
#     assert obj.key['requesting_run'] is None
#
#     # Test with default values
#     obj = Objective(key=ObjectiveKey())
#     assert obj.key['outcome'] is None
#     assert obj.key['inputs'] == {}
#     assert obj.key['requesting_run'] is None


# async def test_objective_future_results():
#     # Test basic future functionality
#     key = ObjectiveKey(outcome="test")
#     obj = Objective(key=key)
#
#     # Test setting and getting a result
#     sub_objective = obj.get_or_create_sub_objective("test_outcome", None)
#     sub_objective.result_future.set_result("test_result")
#     objective1 = obj.get_or_create_sub_objective("test_outcome", None)
#     result = objective1.result_future.result()
#     assert result == "test_result"
#
#     # Test setting and getting a result with args_key
#     args_key = {"args": (1, 2), "kwargs": {}}
#     objective = obj.get_or_create_sub_objective("test_outcome", args_key)
#     objective.result_future.set_result("test_result_with_args")
#     objective2 = obj.get_or_create_sub_objective("test_outcome", args_key)
#     result = objective2.result_future.result()
#     assert result == "test_result_with_args"
#
#     # Test getting non-existent result
#     objective3 = obj.get_or_create_sub_objective("non_existent", None)
#
#     with pytest.raises(InvalidStateError):
#         objective3.result_future.result()
#
#     # Test getting result with non-existent args_key
#     inputs = {"args": (3, 4), "kwargs": {}}
#     objective4 = obj.get_or_create_sub_objective("test_outcome", inputs)
#     with pytest.raises(InvalidStateError):
#         objective4.result_future.result()


# async def test_run_future_results(test_context):
#     # Test that Run's set_result and get_result properly use Objective's future system
#     key = ObjectiveKey(outcome="test")
#     run = Transaction(
#         objective=Objective(key=key),
#         context=test_context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={}
#     )
#
#     # Test setting and getting a result
#     run.objective.set_future_result("test_outcome", None, "test_result")
#     result = run.objective.get_future_result("test_outcome", None)
#     assert result == "test_result"
#
#     # Test setting and getting a result with args_key
#     args_key = {"args": (1, 2), "kwargs": {}}
#     run.objective.set_future_result("test_outcome", args_key, "test_result_with_args")
#     result = run.objective.get_future_result("test_outcome", args_key)
#     assert result == "test_result_with_args"
#
#     # Test getting non-existent result
#     result = run.objective.get_future_result("non_existent", None)
#     assert result is None
#
#     # Test getting result with non-existent args_key
#     key = {"args": (3, 4), "kwargs": {}}
#     result = run.objective.get_future_result("test_outcome", key)
#     assert result is None


# async def test_objective_future_fallback():
#     # Test that when a result is set without args_key, it's used as a fallback
#     obj = Objective(key=ObjectiveKey(outcome="test"))
#
#     # Set a result without args_key
#     obj.set_future_result("test_outcome", None, "fallback_result")
#
#     # Test that any args_key returns the fallback result when use_fallback is True
#     result1 = obj.get_future_result("test_outcome", {"args": (1, 2), "kwargs": {}}, use_fallback=True)
#     assert result1 == "fallback_result"
#
#     result2 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
#     assert result2 == "fallback_result"
#
#     # Test that setting a specific args_key overrides the fallback
#     args_key = {"args": (1, 2), "kwargs": {}}
#     obj.set_future_result("test_outcome", args_key, "specific_result")
#
#     # The specific args_key should get its result
#     result3 = obj.get_future_result("test_outcome", args_key)
#     assert result3 == "specific_result"
#
#     # Other args_keys should still get the fallback when use_fallback is True
#     result4 = obj.get_future_result("test_outcome", {"args": (3, 4), "kwargs": {}}, use_fallback=True)
#     assert result4 == "fallback_result"


# async def test_run_future_fallback(test_context):
#     # Test that Run's result methods properly handle the fallback behavior
#     run = Transaction(
#         objective=Objective(key=ObjectiveKey(outcome="test")),
#         context=test_context,
#         emits={},
#         consumes={},
#         state={},
#         daemons={}
#     )
#
#     # Set a result without args_key
#     run.objective.set_future_result("test_outcome", None, "fallback_result")
#
#     # Test that any args_key returns the fallback result when use_fallback is True
#     key = {"args": (1, 2), "kwargs": {}}
#     result1 = run.objective.get_future_result("test_outcome", key, True)
#     assert result1 == "fallback_result"
#
#     key1 = {"args": (3, 4), "kwargs": {}}
#     result2 = run.objective.get_future_result("test_outcome", key1, True)
#     assert result2 == "fallback_result"
#
#     # Test that setting a specific args_key overrides the fallback
#     args_key = {"args": (1, 2), "kwargs": {}}
#     run.objective.set_future_result("test_outcome", args_key, "specific_result")
#
#     # The specific args_key should get its result
#     result3 = run.objective.get_future_result("test_outcome", args_key, False)
#     assert result3 == "specific_result"
#
#     # Other args_keys should still get the fallback when use_fallback is True
#     key2 = {"args": (3, 4), "kwargs": {}}
#     result4 = run.objective.get_future_result("test_outcome", key2, True)
#     assert result4 == "fallback_result"


# def test_objective_dump_graph():
#     # Create a root objective
#     root = Objective(key=ObjectiveKey(outcome="root", inputs={"root_input": "value"}))
#
#     # Create some sub-objectives
#     sub1 = root.get_or_create_sub_objective("child1", {"child1_input": "value1"})
#     root.get_or_create_sub_objective("child2", {"child2_input": "value2"})
#
#     # Create a sub-sub-objective
#     sub1.get_or_create_sub_objective("grandchild1", {"grandchild1_input": "value3"})
#
#     # Get the graph representation
#     graph = root.dump_graph()
#
#     # Verify the structure
#     assert "root" in graph
#     assert "child1" in graph
#     assert "child2" in graph
#     assert "grandchild1" in graph
#     assert "{'root_input': 'value'}" in graph
#     assert "{'child1_input': 'value1'}" in graph
#     assert "{'child2_input': 'value2'}" in graph
#     assert "{'grandchild1_input': 'value3'}" in graph
#
#     # Verify indentation structure
#     lines = graph.split("\n")
#     assert lines[0].startswith("└──")  # Root level
#     assert all(line.startswith("    ") for line in lines[1:])  # Indented children


def test_create_child_transaction(test_context):
    # Create parent transaction
    parent_objective = Objective(key=ObjectiveKey(outcome="parent", inputs={"parent_input": "value"}))
    parent = Transaction(objective=parent_objective, context=test_context)

    # Create child transaction using helper
    child = parent.create_child_transaction(
        outcome="child",
        inputs={"child_input": "child_value"}
    )

    # Verify child objective is linked to parent
    assert child.objective.of is parent.objective
    assert child.objective.key['outcome'] == "child"
    assert child.objective.key['inputs'] == {"child_input": "child_value"}
    # assert child.objective.key['requesting_run'] is parent

    # Verify context was copied
    assert child.context == parent.context
    assert child.context is not parent.context  # Should be a copy

    # Verify bound_contexts was added to async_context_managers
    assert len(child.async_context_managers) > 0


async def test_child_transaction_context_binding():
    """Test that child transactions properly bind contexts when used"""
    from taskmates.core.workflow_engine.run_context import RunContext

    test_context = RunContext(
        runner_environment={"markdown_path": "test.md", "cwd": "/tmp"},
        run_opts={"model": "test", "max_steps": 10}
    )

    # Track signal connections
    parent_signals_sent = []
    child_signals_sent = []

    # Create parent transaction
    parent = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="parent")),
        context=test_context
    )

    # Connect handlers to track signals
    async def parent_handler(sender, **kwargs):
        parent_signals_sent.append(("parent", sender))

    async def child_handler(sender, **kwargs):
        child_signals_sent.append(("child", sender))

    parent.emits["control"].interrupt.connect(parent_handler)

    # Create child transaction
    child = parent.create_child_transaction(outcome="child")
    child.emits["control"].interrupt.connect(child_handler)

    # Use the transactions
    async with parent.async_transaction_context():
        async with child.async_transaction_context():
            # Send signal from parent - should propagate to child
            await parent.emits["control"].interrupt.send_async({})

    # Verify signal propagation
    assert len(parent_signals_sent) == 1
    assert len(child_signals_sent) == 1  # Child should receive parent's signal


def test_transaction_unified_state_management():
    """Test the unified state management in Transaction"""
    # Create a transaction
    test_context = RunContext(
        runner_environment={"taskmates_dirs": [], "markdown_path": "test.md", "cwd": "/tmp"},
        run_opts={"model": "test", "max_steps": 10}
    )

    transaction = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="test")),
        context=test_context
    )

    # Initial state - future not done, no interrupt
    assert not transaction.result_future.done()
    assert transaction.interrupt_state.value is None
    assert not transaction.is_terminated()

    # Test interrupt states
    transaction.interrupt_state.value = "interrupting"
    assert not transaction.is_terminated()  # Still running, just interrupting

    transaction.interrupt_state.value = "interrupted"
    assert transaction.is_terminated()

    transaction.interrupt_state.value = "killed"
    assert transaction.is_terminated()

    # Reset and test future completion
    transaction.interrupt_state.value = None
    transaction.result_future.set_result("test_result")
    assert transaction.result_future.done()
    assert transaction.is_terminated()
    assert transaction.result_future.result() == "test_result"

    # Test future with exception
    transaction = Transaction(
        objective=Objective(key=ObjectiveKey(outcome="test2")),
        context=test_context
    )
    test_error = ValueError("test error")
    transaction.result_future.set_exception(test_error)
    assert transaction.result_future.done()
    assert transaction.is_terminated()
    with pytest.raises(ValueError, match="test error"):
        transaction.result_future.result()


@pytest.fixture
def test_context() -> RunContext:
    return RunContext(
        runner_environment={
            "taskmates_dirs": [],
            "markdown_path": "test.md",
            "cwd": "/tmp",
            "request_id": "test-request"
        },
        run_opts={
            "model": "test",
            "max_steps": 10
        }
    )


async def test_transactional_operation(test_context):
    """Test creating a transactional operation."""
    from taskmates.core.workflow_engine.transactions.transactional import transactional

    @transactional
    async def test_operation(data: str) -> str:
        return f"processed: {data}"

    result = await test_operation(data="test")

    assert result == "processed: test"


async def test_wrap_with_custom_outcome(test_context):
    """Test wrapping with custom outcome name."""
    from taskmates.core.workflow_engine.transactions.transactional import transactional

    @transactional(outcome="custom_name")
    async def test_operation(data: str) -> str:
        tx = runtime.transaction
        return tx.objective.key['outcome']

    result = await test_operation(data="test")

    assert result == "custom_name"


def test_get_default_manager():
    """Test getting the default manager."""
    manager1 = get_default_transaction_manager()
    manager2 = get_default_transaction_manager()

    # Should return the same instance
    assert manager1 is manager2


def test_transaction_manager_context(test_context):
    """Test using a custom manager via context."""
    custom_manager = TransactionManager()

    with runtime.transaction_manager_context(custom_manager):
        active_manager = runtime.transaction_manager()
        assert active_manager is custom_manager

    # After exiting context, should fall back to default
    active_manager = runtime.transaction_manager()
    assert active_manager is not custom_manager


async def test_outcome_derivation():
    """Test that outcomes are correctly derived from function/method names."""
    from taskmates.core.workflow_engine.run_context import RunContext
    from taskmates.core.workflow_engine.transactions.transactional import transactional

    test_context = RunContext(
        runner_environment={
            "taskmates_dirs": [],
            "markdown_path": "test.md",
            "cwd": "/tmp",
            "request_id": "test-request"
        },
        run_opts={
            "model": "test",
            "max_steps": 10
        }
    )

    # Test 1: Instance method uses __qualname__
    class TestWorkflow:
        @transactional
        async def fulfill(self, test: str) -> str:
            tx = runtime.transaction
            return tx.objective.key['outcome']

    workflow = TestWorkflow()
    outcome = await workflow.fulfill(test='value')
    assert 'TestWorkflow.fulfill' in outcome
    print(f"✓ Instance method outcome: {outcome}")

    # Test 2: Standalone function uses __qualname__
    @transactional
    async def standalone_op(data: str) -> str:
        tx = runtime.transaction
        return tx.objective.key['outcome']

    outcome = await standalone_op(data='test')
    assert 'standalone_op' in outcome
    print(f"✓ Standalone function outcome: {outcome}")

    # Test 3: Custom outcome overrides default
    class CustomWorkflow:
        @transactional(outcome="CustomOutcome.v2")
        async def fulfill(self, inputs: dict) -> str:
            tx = runtime.transaction
            return tx.objective.key['outcome']

    workflow = CustomWorkflow()
    outcome = await workflow.fulfill(inputs={'test': 'value'})
    assert outcome == "CustomOutcome.v2"
    print(f"✓ Custom outcome: {outcome}")

# TODO
# async def test_in_memory_caching():
#     """Test that in-memory caching works correctly."""
#     from taskmates.core.workflow_engine.transactions.transactional import transactional
#
#     # Create a manager with in-memory cache
#     manager = TransactionManager(cache_dir=None)
#
#     call_count = 0
#
#     @transactional
#     async def counting_operation(value: int) -> int:
#         nonlocal call_count
#         call_count += 1
#         return value * 2
#
#     # First call should execute
#     with runtime.transaction_manager_context(manager):
#         result1 = await counting_operation(value=5)
#         assert result1 == 10
#         assert call_count == 1
#
#         # Second call with same inputs should use cache
#         result2 = await counting_operation(value=5)
#         assert result2 == 10
#         assert call_count == 1  # Should not increment
#
#         # Call with different inputs should execute
#         result3 = await counting_operation(value=7)
#         assert result3 == 14
#         assert call_count == 2


async def test_file_based_caching(tmp_path):
    """Test that file-based caching works correctly."""
    from taskmates.core.workflow_engine.transactions.transactional import transactional

    # Create a manager with file-based cache
    cache_dir = tmp_path / "cache"
    manager = TransactionManager(cache_dir=str(cache_dir))

    call_count = 0

    @transactional
    async def counting_operation(value: int) -> int:
        nonlocal call_count
        call_count += 1
        return value * 2

    # First call should execute and cache to file
    with runtime.transaction_manager_context(manager):
        result1 = await counting_operation(value=5)
        assert result1 == 10
        assert call_count == 1

        # Verify cache file was created
        assert cache_dir.exists()
        cache_files = list(cache_dir.rglob("result.yml"))
        assert len(cache_files) == 1

        # Second call should use file cache
        result2 = await counting_operation(value=5)
        assert result2 == 10
        assert call_count == 1


# async def test_default_manager_uses_memory_cache():
#     """Test that the default manager uses in-memory caching."""
#     from taskmates.core.workflow_engine.transactions.transactional import transactional
#
#     # Reset default manager
#     global _default_manager
#     _default_manager = None
#
#     manager = get_default_transaction_manager()
#     assert manager.cache_dir is None
#     assert isinstance(manager._memory_cache, dict)
#
#     call_count = 0
#
#     @transactional
#     async def test_op(x: int) -> int:
#         nonlocal call_count
#         call_count += 1
#         return x + 1
#
#     # Should use default manager with memory cache
#     result1 = await test_op(x=1)
#     assert result1 == 2
#     assert call_count == 1
#
#     result2 = await test_op(x=1)
#     assert result2 == 2
#     assert call_count == 1  # Cached


async def test_memory_cache_isolation():
    """Test that different managers have isolated memory caches."""
    from taskmates.core.workflow_engine.transactions.transactional import transactional

    manager1 = TransactionManager(cache_dir=None)
    manager2 = TransactionManager(cache_dir=None)

    call_count = 0

    @transactional
    async def test_op(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # Execute with manager1
    with runtime.transaction_manager_context(manager1):
        result1 = await test_op(x=5)
        assert result1 == 10
        assert call_count == 1

    # Execute with manager2 - should not use manager1's cache
    with runtime.transaction_manager_context(manager2):
        result2 = await test_op(x=5)
        assert result2 == 10
        assert call_count == 2  # Should execute again


# async def test_has_cached_result_memory():
#     """Test has_cached_result with in-memory cache."""
#     manager = TransactionManager(cache_dir=None)
#
#     # Initially no cache
#     assert not manager.has_cached_result("test_op", {"x": 1})
#
#     # Set a result
#     manager.set_cached_result("test_op", {"x": 1}, 42)
#
#     # Now should have cache
#     assert manager.has_cached_result("test_op", {"x": 1})
#
#     # Different inputs should not have cache
#     assert not manager.has_cached_result("test_op", {"x": 2})


# async def test_get_cached_result_memory():
#     """Test get_cached_result with in-memory cache."""
#     manager = TransactionManager(cache_dir=None)
#
#     # Initially returns None
#     assert manager.get_cached_result("test_op", {"x": 1}) is None
#
#     # Set a result
#     manager.set_cached_result("test_op", {"x": 1}, {"result": 42})
#
#     # Should retrieve the result
#     result = manager.get_cached_result("test_op", {"x": 1})
#     assert result == {"result": 42}
#
#     # Different inputs should return None
#     assert manager.get_cached_result("test_op", {"x": 2}) is None
