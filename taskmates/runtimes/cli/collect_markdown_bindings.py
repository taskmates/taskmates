from typeguard import typechecked

from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.lib.contextlib_.ensure_async_context_manager import ensure_async_context_manager
from taskmates.runtimes.cli.signals.incoming_messages_formatting_processor import \
    IncomingMessagesFormattingProcessor


@typechecked
class CollectMarkdownBindings:
    def __init__(self, transaction: Transaction, markdown_chat: MarkdownChat):
        self.transaction = transaction
        self.markdown_chat = markdown_chat

    async def __aenter__(self):
        daemons = [
            ensure_async_context_manager(MarkdownChatDaemon(
                execution_environment_signals=self.transaction.consumes["execution_environment"],
                markdown_chat_state=self.markdown_chat
            )),
            ensure_async_context_manager(IncomingMessagesFormattingProcessor(
                execution_environment_signals=self.transaction.consumes["execution_environment"],
            ))
        ]

        # Add daemons to transaction's async exit stack
        for daemon in daemons:
            await self.transaction.async_exit_stack.enter_async_context(daemon)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup is handled by transaction.async_exit_stack
        pass
