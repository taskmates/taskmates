from typeguard import typechecked

from taskmates.workflow_engine.run import RUN
from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.actions.get_incoming_markdown import get_incoming_markdown
from taskmates.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.workflows.markdown_complete import MarkdownComplete
from taskmates.workflows.signals.processors.incoming_messages_formatting_processor import \
    IncomingMessagesFormattingProcessor
from taskmates.workflows.states.markdown_chat import MarkdownChat


class CliComplete(Workflow):
    @typechecked
    async def steps(self,
                    incoming_messages: list[str],
                    response_format: str = "text",
                    history_path: str | None = None
                    ):
        run = RUN.get()

        with (run
                      .fork()
                      .request(outcome="incoming_markdown")
                      .attempt(daemons=[MarkdownChatDaemon(),
                                        IncomingMessagesFormattingProcessor()],
                               state={"markdown_chat": MarkdownChat()}
                               )):
            markdown_chat = await get_incoming_markdown(history_path, incoming_messages)

        return await MarkdownComplete().fulfill(
            markdown_chat=markdown_chat
        )
