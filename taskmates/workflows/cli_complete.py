from typeguard import typechecked

from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.actions.get_incoming_markdown import get_incoming_markdown
from taskmates.workflows.markdown_complete import MarkdownComplete


class CliComplete(Workflow):
    @typechecked
    async def steps(self,
                    incoming_messages: list[str],
                    response_format: str = "text",
                    history_path: str | None = None
                    ):
        markdown_chat = await get_incoming_markdown(history_path, incoming_messages)

        return await MarkdownComplete().fulfill(
            markdown_chat=markdown_chat
        )
