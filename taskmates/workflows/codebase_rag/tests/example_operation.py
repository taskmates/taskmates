from taskmates.core.workflow_engine.transaction_manager import runtime


async def example_operation(value: int) -> int:
    """Example operation that uses transaction logging."""
    runtime.logger.info(f"Starting operation with value: {value}")
    runtime.logger.debug(f"Processing value: {value}")

    result = value * 2

    runtime.logger.info(f"Operation completed with result: {result}")

    return result


async def another_operation(text: str) -> str:
    """Another example that demonstrates logging."""
    runtime.logger.info(f"Processing text: {text}")

    if not text:
        runtime.logger.warning("Empty text provided")
        return ""

    result = text.upper()

    runtime.logger.info(f"Transformed text to: {result}")

    return result
