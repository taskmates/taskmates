import os

from loguru import logger

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.assistances.chat_completion.markdown_chat_completion_assistance import MarkdownChatCompletionAssistance
from taskmates.assistances.code_execution.jupyter_.markdown_code_cells_assistance import MarkdownCodeCellsAssistance
from taskmates.assistances.code_execution.tool_.markdown_tools_assistance import MarkdownToolsAssistance
from taskmates.assistances.completion_context import CompletionContext
from taskmates.signals import Signals


class MarkdownCompletionAssistance:
    async def perform_completion(self, context: CompletionContext, markdown_chat: str, signals: Signals):
        try:
            taskmates_dir = context.get("taskmates_dir", os.environ.get("TASKMATES_PATH", "/var/tmp/taskmates"))
            interactive = context.get("interactive", True)

            markdown_chunks = []

            async def append_markdown(markdown):
                if markdown is not None:
                    markdown_chunks.append(markdown)

            with signals.request.connected_to(append_markdown), \
                    signals.formatting.connected_to(append_markdown):

                if not markdown_chat.lstrip().startswith("**") and not markdown_chat.lstrip().startswith("--"):
                    await signals.request.send_async(f"**user** ")

                await signals.request.send_async(markdown_chat)

                line_breaks = await self.compute_linebreaks(markdown_chat)
                if line_breaks:
                    await signals.formatting.send_async(line_breaks)

            interrupted = False

            async def handle_interrupted(sender):
                nonlocal interrupted
                interrupted = True

            await signals.start.send_async({})

            current_interaction = 0
            max_interactions = context.get("max_interactions", float('inf'))
            while True:
                with signals.interrupt.connected_to(handle_interrupted), \
                        signals.completion.connected_to(append_markdown):

                    if interrupted:
                        logger.debug("Interrupted")
                        break

                    current_markdown = "".join(markdown_chunks)

                    logger.debug(f"Parsing markdown chat")
                    chat: dict = await parse_markdown_chat(markdown_chat=current_markdown,
                                                           markdown_path=context["markdown_path"],
                                                           taskmates_dir=taskmates_dir,
                                                           template_params=context.get("template_params"))
                    if chat["model"] is None:
                        del chat["model"]
                    if "model" in context:
                        chat.setdefault("model", context["model"])

                    if "metadata" in chat and "cwd" in chat["metadata"]:
                        context = {**context}
                        context["cwd"] = chat["metadata"].get("cwd")

                    logger.debug(f"Computing next completion assistance")
                    completion_assistance = self.get_next_completion(chat)
                    logger.debug(f"Next completion assistance: {completion_assistance}")

                    if completion_assistance:
                        current_interaction += 1

                        if current_interaction > max_interactions:
                            break

                        if current_interaction > 1:
                            line_breaks = await self.compute_linebreaks(current_markdown)
                            if line_breaks:
                                await signals.response.send_async(line_breaks)

                        await completion_assistance.perform_completion(context, chat, signals)
                    else:
                        break

            logger.debug(f"Finished completion assistance")

            if interactive and not interrupted:
                line_breaks = await self.compute_linebreaks(current_markdown)
                if line_breaks:
                    await signals.next_responder.send_async(line_breaks)

                recipient = chat["last_message"]["recipient"]
                if recipient:
                    await signals.next_responder.send_async(f"**{recipient}** ")

            await signals.success.send_async({})

        except Exception as e:
            logger.exception(e)
            await signals.error.send_async(e)
            # raise e

    async def compute_linebreaks(self, current_markdown):
        padding = ""
        if not current_markdown.endswith("\n\n"):
            if current_markdown.endswith("\n"):
                padding = "\n"
            else:
                padding = "\n\n"
        return padding

    @staticmethod
    def get_next_completion(chat):
        assistances = [
            MarkdownCodeCellsAssistance(),
            MarkdownToolsAssistance(),
            MarkdownChatCompletionAssistance()
        ]

        for assistance in assistances:
            if assistance.can_complete(chat):
                return assistance

        return None
