from typing import TypedDict

from typeguard import typechecked

from taskmates.core.workflow_engine.transaction import Transaction
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.compute_next_completion import compute_next_completion
from taskmates.logging import logger, file_logger


@typechecked
class CompletionStepTransaction(Transaction):
    """Transaction for handling a single completion step within MarkdownCompletion."""

    class State(TypedDict):
        pass  # This transaction doesn't need its own state

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # CompletionStepTransaction doesn't need additional initialization
        # It inherits all necessary signals and state from parent Transaction

    async def fulfill(self) -> bool:
        """Execute a single completion step and return whether to continue."""
        chat_payload = self.objective.key['inputs']['chat_payload']

        file_logger.debug("parsed_chat.json", content=chat_payload)

        completion_assistance: CompletionProvider | None = compute_next_completion(chat_payload)
        logger.debug(f"Next completion: {completion_assistance}")

        if not completion_assistance:
            return False

        await completion_assistance.perform_completion(
            chat_payload,
            self.emits["control"],
            self.consumes["execution_environment"],
            self.consumes["status"]
        )

        return True


async def test_completion_step_transaction(tmp_path):
    from taskmates.core.workflow_engine.run_context import RunContext
    from taskmates.core.workflow_engine.transaction import Objective, ObjectiveKey

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
    from taskmates.core.workflows.markdown_completion.build_chat_completion_request import build_chat_completion_request

    markdown_chat = "**user>** Hello\n\n**assistant>** Hi!\n\n"

    # Build the payload without needing transaction context
    chat_payload = build_chat_completion_request(
        markdown_chat,
        markdown_path=str(tmp_path / "test.md")
    )

    step_transaction = parent.create_child_transaction(
        outcome="MarkdownCompletion-step-1",
        inputs={"chat_payload": chat_payload},
        transaction_class=CompletionStepTransaction
    )

    # Verify it's the correct type
    assert isinstance(step_transaction, CompletionStepTransaction)
    assert step_transaction.objective.of is parent.objective
    assert step_transaction.objective.key['outcome'] == "MarkdownCompletion-step-1"

    # Test fulfill method
    async def noop(sender, **kwargs):
        pass

    # Connect signals
    parent.emits["control"].interrupt.connect(noop)
    parent.consumes["execution_environment"].response.connect(noop)

    async with parent.async_transaction_context():
        async with step_transaction.async_transaction_context():
            # Test that fulfill works
            should_continue = await step_transaction.fulfill()

            # Should return False because the chat is complete
            assert should_continue is False
