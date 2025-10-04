from typeguard import typechecked

from taskmates.core.workflow_engine.transaction import Transaction
from taskmates.core.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.lib.contextlib_.stacked_contexts import ensure_async_context_manager
from taskmates.runtimes.cli.read_history import read_history
from taskmates.runtimes.cli.signals.incoming_messages_formatting_processor import \
    IncomingMessagesFormattingProcessor


@typechecked
class GetIncomingMarkdown(Transaction):
    def __init__(self, **kwargs):
        # Initialize parent Transaction
        super().__init__(**kwargs)

        # Initialize state
        self.state["markdown_chat"] = MarkdownChat()

        # Create async context managers
        self.async_context_managers = list(self.async_context_managers) + [
            ensure_async_context_manager(MarkdownChatDaemon(
                execution_environment_signals=self.consumes["execution_environment"],
                markdown_chat_state=self.state["markdown_chat"]
            )),

            ensure_async_context_manager(IncomingMessagesFormattingProcessor(
                execution_environment_signals=self.consumes["execution_environment"],
            ))
        ]

    async def fulfill(self) -> str:
        async with self.async_transaction_context():
            history_path = self.objective.key['inputs'].get('history_path')
            incoming_messages = self.objective.key['inputs'].get('incoming_messages', [])

            if history_path:
                history = read_history(history_path)
                if history:
                    await self.consumes["execution_environment"].response.send_async(sender="history", value=history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await self.consumes["execution_environment"].response.send_async(
                        sender="incoming_message", value=incoming_message)

            markdown_chat = self.state["markdown_chat"].get()["full"]
            return markdown_chat
