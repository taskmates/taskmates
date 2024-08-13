from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.contexts import Contexts, CONTEXTS
from taskmates.core.completion_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.core.handlers.env_manager import EnvManager
from taskmates.core.handlers.full_markdown_collector import FullMarkdownCollector
from taskmates.core.handlers.interrupt_request_handler import InterruptRequestHandler
from taskmates.core.handlers.interrupted_or_killed_handler import InterruptedOrKilledHandler
from taskmates.io.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.lib.context_.context_fork import context_fork
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.sdk.handlers.return_value_processor import ReturnValueProcessor
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class CompletionEngine:
    @typechecked
    async def perform_completion(self,
                                 history: str | None,
                                 incoming_messages: list[str],
                                 contexts: Contexts,
                                 signals: Signals
                                 ):
        interactive = contexts['client_config']["interactive"]

        markdown_collector = FullMarkdownCollector()
        incoming_messages_formatting_processor = IncomingMessagesFormattingProcessor(signals)
        return_value_processor = ReturnValueProcessor()
        interruption_handler = InterruptedOrKilledHandler()
        interrupt_request_handler = InterruptRequestHandler(signals)

        env_manager = EnvManager()

        request_handlers = [markdown_collector,
                            incoming_messages_formatting_processor,
                            interrupt_request_handler,
                            interruption_handler,
                            return_value_processor,
                            env_manager]

        with signals.connected_to(request_handlers):

            # Input
            if history:
                await signals.input.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.input.incoming_message.send_async(incoming_message)

            # Lifecycle: Start
            await signals.lifecycle.start.send_async({})

            current_step = 0
            while True:
                with context_fork(CONTEXTS) as step_contexts:

                    current_markdown = markdown_collector.get_current_markdown()

                    logger.debug(f"Parsing markdown chat")
                    markdown_path = contexts["completion_context"]["markdown_path"]
                    chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                           markdown_path=markdown_path,
                                                           taskmates_dirs=(
                                                               contexts['completion_opts'].get("taskmates_dirs")),
                                                           template_params=contexts['completion_opts'][
                                                               "template_params"])

                    if "model" in chat["metadata"]:
                        contexts['completion_opts']["model"] = chat["metadata"]["model"]

                    if contexts['completion_opts']["model"] in ("quote", "echo"):
                        contexts['completion_opts']["max_steps"] = 1

                    logger.debug(f"Computing next completion assistance")
                    completion_assistance = compute_next_completion(chat, contexts['completion_opts'])

                    logger.debug(f"Next completion assistance: {completion_assistance}")
                    if not completion_assistance:
                        break

                    # Pre-Step
                    current_step += 1

                    if current_step > contexts['completion_opts']["max_steps"]:
                        break

                    if current_step > 1:
                        separator = compute_separator(current_markdown)
                        if separator:
                            await signals.response.response.send_async(separator)

                    # Step
                    await completion_assistance.perform_completion(chat, step_contexts, signals)

                    # TODO: Add lifecycle/checkpoint here

                    # Post-Step
                    if return_value_processor.return_value is not NOT_SET:
                        logger.debug(f"Return value is set to: {return_value_processor.return_value}")
                        break

                    if interruption_handler.interrupted_or_killed:
                        logger.debug("Interrupted")
                        break

            logger.debug(f"Finished completion assistance")

            # TODO: Add lifecycle/checkpoint here

            separator = compute_separator(markdown_collector.get_current_markdown())
            if separator:
                await signals.response.formatting.send_async(separator)

            # Post-Completion
            if interactive and not interruption_handler.interrupted_or_killed:
                recipient = chat["messages"][-1]["recipient"]
                if recipient:
                    await signals.response.next_responder.send_async(f"**{recipient}>** ")

            # Lifecycle: Success
            await signals.lifecycle.success.send_async({})
