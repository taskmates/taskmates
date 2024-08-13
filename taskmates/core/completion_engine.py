from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.contexts import Contexts, CONTEXTS
from taskmates.core.completion_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.core.signal_receivers.current_markdown import CurrentMarkdown
from taskmates.core.signal_receivers.current_step import CurrentStep
from taskmates.core.signal_receivers.interrupt_request_collector import InterruptRequestCollector
from taskmates.core.signal_receivers.interrupted_or_killed_collector import InterruptedOrKilledCollector
from taskmates.core.signal_receivers.max_steps_manager import MaxStepsManager
from taskmates.io.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.lib.context_.context_fork import context_fork
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector
from taskmates.signals.signals import Signals
from taskmates.types import Chat
from taskmates.sdk.extension_manager import EXTENSION_MANAGER


class CompletionEngine:
    @typechecked
    async def perform_completion(self,
                                 history: str | None,
                                 incoming_messages: list[str],
                                 contexts: Contexts,
                                 signals: Signals,
                                 states: dict,
                                 ):

        with EXTENSION_MANAGER.get().completion_context(
            history, incoming_messages, contexts, signals, states
        ) as (history, incoming_messages, current_contexts, signals, states):
            interactive = current_contexts['client_config']["interactive"]

            incoming_messages_formatting_processor = IncomingMessagesFormattingProcessor(signals)
            return_value_processor = ReturnValueCollector()
            interruption_handler = InterruptedOrKilledCollector()
            interrupt_request_handler = InterruptRequestCollector(signals)

            max_steps_manager = MaxStepsManager()

            states.update({
                "current_markdown": CurrentMarkdown(),
                "current_step": CurrentStep(),
            })

            request_handlers = [states["current_markdown"],
                                incoming_messages_formatting_processor,
                                interrupt_request_handler,
                                interruption_handler,
                                return_value_processor]

            with signals.connected_to(request_handlers):

                # Input
                if history:
                    await signals.input.history.send_async(history)

                for incoming_message in incoming_messages:
                    if incoming_message:
                        await signals.input.incoming_message.send_async(incoming_message)

                # Lifecycle: Start
                await signals.lifecycle.start.send_async({})

                markdown_path = current_contexts["completion_context"]["markdown_path"]
                taskmates_dirs = current_contexts['completion_opts'].get("taskmates_dirs")
                template_params = current_contexts['completion_opts']["template_params"]

                # TODO: we need an interface for control flow extensions that encapsulates all these should_break logic

                while True:
                    # TODO reload from file system
                    current_markdown = states["current_markdown"].get()

                    chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                           markdown_path=markdown_path,
                                                           taskmates_dirs=taskmates_dirs,
                                                           template_params=template_params)

                    # Pre-Step
                    states["current_step"].increment()

                    should_break = await self.perform_step(
                        chat, current_contexts, signals, return_value_processor,
                        interruption_handler, max_steps_manager, states
                    )
                    if should_break:
                        break

                logger.debug(f"Finished completion assistance")

                # TODO: Add lifecycle/checkpoint here

                # TODO reload from file system
                separator = compute_separator(states["current_markdown"].get())
                if separator:
                    await signals.response.formatting.send_async(separator)

                # Post-Completion
                if interactive and not interruption_handler.interrupted_or_killed:
                    recipient = chat["messages"][-1]["recipient"]
                    if recipient:
                        await signals.response.next_responder.send_async(f"**{recipient}>** ")

                # Lifecycle: Success
                await signals.lifecycle.success.send_async({})

    @staticmethod
    async def perform_step(chat: Chat, contexts: Contexts, signals: Signals,
                           return_value_processor, interruption_handler, max_steps_manager, states):
        with temp_context(CONTEXTS, contexts) as step_contexts:
            with EXTENSION_MANAGER.get().completion_step_context(
                chat, step_contexts, signals, return_value_processor,
                interruption_handler, max_steps_manager, states
            ) as (chat, step_contexts, signals, return_value_processor,
                  interruption_handler, max_steps_manager, states):

                # enrich context
                step_contexts['step_context']['current_step'] = states["current_step"].get()

                if "model" in chat["metadata"]:
                    step_contexts['completion_opts']["model"] = chat["metadata"]["model"]

                if step_contexts['completion_opts']["model"] in ("quote", "echo"):
                    step_contexts['completion_opts']["max_steps"] = 1

                # Compute Next Completion
                logger.debug(f"Computing next completion assistance")
                completion_assistance = compute_next_completion(chat, step_contexts['completion_opts'])
                logger.debug(f"Next completion assistance: {completion_assistance}")

                # Guards
                if not completion_assistance:
                    return True

                if max_steps_manager.should_break(step_contexts):
                    return True

                if return_value_processor.return_value is not NOT_SET:
                    logger.debug(f"Return value is set to: {return_value_processor.return_value}")
                    return True

                if interruption_handler.interrupted_or_killed:
                    logger.debug("Interrupted")
                    return True

                # Pre-Step
                if step_contexts['step_context']['current_step'] > 1:
                    separator = compute_separator(chat['markdown_chat'])
                    if separator:
                        await signals.response.response.send_async(separator)

                # Step
                await completion_assistance.perform_completion(chat, step_contexts, signals)

                # Post-Step
                # TODO: Add lifecycle/checkpoint here
        return False
