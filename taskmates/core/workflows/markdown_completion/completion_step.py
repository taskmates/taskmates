from typing import TypedDict

from typeguard import typechecked

from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.compute_next_completion import compute_next_completion
from taskmates.logging import logger, file_logger


@typechecked
class CompletionStep:
    async def fulfill(self, transaction: Transaction) -> bool:
        """Execute a single completion step and return whether to continue."""
        inputs = transaction.objective.key['inputs']
        chat_payload = inputs['chat_payload']

        file_logger.debug("parsed_chat.json", content=chat_payload)

        completion_assistance: CompletionProvider | None = compute_next_completion(chat_payload)
        logger.debug(f"Next completion: {completion_assistance}")

        if not completion_assistance:
            return False

        await completion_assistance.perform_completion(
            chat_payload,
            transaction.emits["control"],
            transaction.consumes["execution_environment"],
            transaction.consumes["status"]
        )

        # TODO: we should return the completion here
        return True


async def test_completion_step_transaction(tmp_path):
    from taskmates.core.workflow_engine.run_context import RunContext
    from taskmates.core.workflow_engine.objective import Objective
    from taskmates.core.workflow_engine.objective import ObjectiveKey

    # Create test context
    test_context = RunContext(
        runner_environment={
            "taskmates_dirs": [str(tmp_path / ".taskmates")],
            "markdown_path": str(tmp_path / "test.md"),
            "cwd": str(tmp_path),
            "request_id": "test-request"
        },
        run_opts={
            "model": "quote",
            "max_steps": 10
        }
    )

    # Create parent transaction (simulating MarkdownCompletion)
    parent_objective = Objective(key=ObjectiveKey(
        outcome="MarkdownCompletion",
        inputs={"markdown_chat": "Hello"}
    ))
    parent = Transaction(objective=parent_objective, context=test_context)

    # Create CompletionStepTransaction
    from taskmates.core.workflows.markdown_completion.build_completion_request import build_completion_request

    markdown_chat = "**user>** Hello\n\n**assistant>** Hi!\n\n"

    # Build the payload without needing transaction context
    chat_payload = build_completion_request(
        markdown_chat,
        markdown_path=str(tmp_path / "test.md")
    )

    child_transaction = parent.create_child_transaction(
        outcome="MarkdownCompletion-step-1",
        inputs={"chat_payload": chat_payload}
    )

    workflow = CompletionStep()

    # Verify it's the correct type
    assert isinstance(workflow, CompletionStep)
    assert child_transaction.objective.of is parent.objective
    assert child_transaction.objective.key['outcome'] == "MarkdownCompletion-step-1"

    # Test fulfill method
    async def noop(sender, **kwargs):
        pass

    # Connect signals
    parent.emits["control"].interrupt.connect(noop)
    parent.consumes["execution_environment"].response.connect(noop)

    async with parent.async_transaction_context():
        async with child_transaction.async_transaction_context():
            # Test that fulfill works
            should_continue = await workflow.fulfill(child_transaction)

            # Should return False because the chat is complete
            assert should_continue is False
