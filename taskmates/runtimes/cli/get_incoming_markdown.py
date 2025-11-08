from typeguard import typechecked

from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.runtimes.cli.collect_markdown_bindings import CollectMarkdownBindings
from taskmates.runtimes.cli.read_history import read_history


@typechecked
class GetIncomingMarkdown:
    @transactional()
    async def fulfill(self, history_path: str = None, incoming_messages: list = None) -> str:
        get_incoming_markdown_transaction = runtime.transaction

        markdown_chat_state = MarkdownChat()

        async with CollectMarkdownBindings(get_incoming_markdown_transaction, markdown_chat_state):
            if incoming_messages is None:
                incoming_messages = []

            if history_path:
                history = read_history(history_path)
                if history:
                    await get_incoming_markdown_transaction.consumes["execution_environment"].response.send_async(
                        sender="history",
                        value=history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await get_incoming_markdown_transaction.consumes["execution_environment"].response.send_async(
                        sender="incoming_message", value=incoming_message)

            markdown_chat = markdown_chat_state.get()["full"]
            return markdown_chat
