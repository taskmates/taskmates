from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.assistances.chat_completion.markdown_chat_completion_assistance import MarkdownChatCompletionAssistance
from taskmates.assistances.code_execution.jupyter_.markdown_code_cells_assistance import MarkdownCodeCellsAssistance
from taskmates.assistances.code_execution.tool_.markdown_tools_assistance import MarkdownToolsAssistance
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.logging import logger
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class MarkdownCompletionAssistance:
    @typechecked
    async def perform_completion(self,
                                 context: CompletionContext,
                                 markdown_chat: str,
                                 server_config: ServerConfig,
                                 client_config: ClientConfig,
                                 completion_opts: CompletionOpts,
                                 signals: Signals
                                 ):

        taskmates_dir = server_config.get("taskmates_dir")
        interactive = client_config["interactive"]

        markdown_chunks = []
        return_value = None

        async def append_markdown(markdown):
            if markdown is not None:
                markdown_chunks.append(markdown)

        async def process_return_value(status):
            nonlocal return_value
            logger.debug(f"Return status: {status}")
            return_value = status

        with signals.output.request.connected_to(append_markdown), \
                signals.output.formatting.connected_to(append_markdown):

            await signals.output.request.send_async(markdown_chat)

            line_breaks = await self.compute_linebreaks(markdown_chat)
            if line_breaks:
                await signals.output.formatting.send_async(line_breaks)

        interrupted_or_killed = False

        async def handle_interrupted_or_killed(_sender):
            nonlocal interrupted_or_killed
            interrupted_or_killed = True

        interrupt_requested = False

        async def handle_interrupt_request(_sender):
            nonlocal interrupt_requested
            if interrupt_requested:
                logger.info("Interrupt requested again. Killing the request.")
                await signals.control.kill.send_async({})
            else:
                logger.info("Interrupt requested")
                await signals.control.interrupt.send_async({})
                interrupt_requested = True

        await signals.output.start.send_async({})

        current_interaction = 0
        max_interactions = completion_opts["max_interactions"]
        while True:
            with signals.control.interrupt_request.connected_to(handle_interrupt_request), \
                    signals.output.interrupted.connected_to(handle_interrupted_or_killed), \
                    signals.output.killed.connected_to(handle_interrupted_or_killed), \
                    signals.output.completion.connected_to(append_markdown), \
                    signals.output.return_value.connected_to(process_return_value):

                if return_value is not None:
                    logger.debug(f"Return status is not None: {return_value}")
                    break

                if interrupted_or_killed:
                    logger.debug("Interrupted")
                    break

                current_markdown = "".join(markdown_chunks)

                logger.debug(f"Parsing markdown chat")
                chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                       markdown_path=context["markdown_path"],
                                                       taskmates_dir=taskmates_dir,
                                                       template_params=completion_opts["template_params"])

                if "model" in chat["metadata"]:
                    completion_opts["model"] = chat["metadata"]["model"]

                if completion_opts["model"] in ("quote", "echo"):
                    max_interactions = 1

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
                            await signals.output.response.send_async(line_breaks)

                    await completion_assistance.perform_completion(context, chat, signals)
                else:
                    break

        logger.debug(f"Finished completion assistance")

        if interactive and not interrupted_or_killed:
            line_breaks = await self.compute_linebreaks(current_markdown)
            if line_breaks:
                await signals.output.next_responder.send_async(line_breaks)

            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await signals.output.next_responder.send_async(f"**{recipient}>** ")

        await signals.output.success.send_async({})

    @staticmethod
    async def compute_linebreaks(current_markdown):
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
