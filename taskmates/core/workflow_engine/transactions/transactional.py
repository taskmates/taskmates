from typing import Optional, Callable

from taskmates.core.workflow_engine.transaction_manager import TransactionalOperation, runtime


def transactional(
        func: Optional[Callable] = None,
        *,
        max_retries: int = 1,
        initial_delay: float = 1.0,
        outcome: Optional[str] = None
) -> Callable:
    """
    Decorator for async operations and workflow methods.

    Supports two modes:
    1. Workflow method mode: Derives outcome from method's __qualname__
    2. Standalone operation mode: Uses outcome parameter or derives from function name

    Args:
        func: Function to decorate (when used without parens)
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        outcome: Custom name for the transaction outcome (optional)

    Usage:
        # Workflow method without parentheses
        class MyWorkflow:
            @transactional
            async def fulfill(self, inputs: dict) -> str:
                transaction = current_transaction.transaction
                async with MyBindings(transaction, state):
                    return "result"

        # Workflow method with custom outcome
        class MyWorkflow:
            @transactional(outcome="MyWorkflow_v2.fulfill")
            async def fulfill(self, inputs: dict) -> str:
                ...

        # Standalone operation with retry config
        @transactional(max_retries=5, initial_delay=2.0, outcome="my_operation")
        async def my_operation(data: str) -> str:
            return process(data)

        # Direct call
        result = await workflow.fulfill(inputs={...})

        # Build + setup + execute (workflow methods only)
        from taskmates.core.workflow_engine.transaction_manager import runtime
        manager = runtime.get_active_transaction_manager()
        transaction = manager.build_executable_transaction(
            operation=workflow.fulfill.operation,
            outcome=workflow.fulfill.outcome,
            inputs={...},
            workflow_instance=workflow
        )
        async with ExternalBindings(transaction, state):
            result = await transaction()

        # With custom manager
        custom_manager = TransactionManager(context=custom_context)
        with runtime.transaction_manager_context(custom_manager):
            result = await workflow.fulfill(inputs={...})
    """

    def decorator(method: Callable) -> TransactionalOperation:
        return TransactionalOperation(
            operation=method,
            outcome=outcome,
            max_retries=max_retries,
            initial_delay=initial_delay
        )

    # If called without parentheses, func is the function
    if func is not None:
        return decorator(func)

    return decorator


async def test_transactional_without_parentheses():
    """Test using @transactional without parentheses."""
    from taskmates.core.workflow_engine.run_context import RunContext

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

    class TestWorkflow:
        @transactional
        async def fulfill(self, key: str) -> str:
            transaction = runtime.transaction
            assert transaction is not None
            return "result"

    workflow = TestWorkflow()
    result = await workflow.fulfill(key="value")
    assert result == "result"
