import copy

from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.contexts import Contexts, CONTEXTS
from taskmates.core.completion_next_completion import compute_next_step
from taskmates.core.compute_separator import compute_separator
from taskmates.core.signal_receivers.current_markdown import CurrentMarkdown
from taskmates.core.signal_receivers.current_step import CurrentStep
from taskmates.core.signal_receivers.interrupt_request_collector import InterruptRequestCollector
from taskmates.core.signal_receivers.interrupted_or_killed_collector import InterruptedOrKilledCollector
from taskmates.core.signal_receivers.max_steps_manager import MaxStepsManager
from taskmates.io.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.sdk.extension_manager import EXTENSION_MANAGER
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class ChatSession:
    @typechecked
    def __init__(self, history: str | None,
                 incoming_messages: list[str],
                 contexts: Contexts,
                 signals=None,
                 handlers=()):
        if signals is None:
            signals = Signals()

        self.history = history
        self.incoming_messages = incoming_messages
        # TODO: not sure we need to deepcopy here
        self.contexts = copy.deepcopy(contexts)
        self.signals = signals
        self.handlers = handlers
        self.states = {}

        EXTENSION_MANAGER.get().after_build_contexts(self.contexts)

    async def resume(self):
        with temp_context(CONTEXTS, copy.deepcopy(self.contexts)) as run_contexts:
            interactive = run_contexts['client_config']["interactive"]

            signals = self.signals
            states = self.states
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

            with signals.connected_to([*self.handlers, *request_handlers]):
                # Input
                if self.history:
                    await signals.input.history.send_async(self.history)

                for incoming_message in self.incoming_messages:
                    if incoming_message:
                        await signals.input.incoming_message.send_async(incoming_message)

                # Lifecycle: Start
                await signals.lifecycle.start.send_async({})

                markdown_path = run_contexts["completion_context"]["markdown_path"]
                taskmates_dirs = run_contexts['completion_opts'].get("taskmates_dirs")
                template_params = run_contexts['completion_opts']["template_params"]

                while True:
                    current_markdown = states["current_markdown"].get()

                    chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                           markdown_path=markdown_path,
                                                           taskmates_dirs=taskmates_dirs,
                                                           template_params=template_params)

                    # Pre-Step
                    states["current_step"].increment()

                    should_break = await self.perform_step(
                        chat, return_value_processor,
                        interruption_handler, max_steps_manager
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

    async def perform_step(self,
                           chat: Chat,
                           return_value_processor,
                           interruption_handler,
                           max_steps_manager):
        with temp_context(CONTEXTS, self.contexts) as step_contexts:
            signals = self.signals
            states = self.states

            # Enrich context
            step_contexts['step_context']['current_step'] = states["current_step"].get()

            if "model" in chat["metadata"]:
                step_contexts['completion_opts']["model"] = chat["metadata"]["model"]

            if step_contexts['completion_opts']["model"] in ("quote", "echo"):
                step_contexts['completion_opts']["max_steps"] = 1

            # Guards
            if max_steps_manager.should_break(step_contexts):
                return True

            if return_value_processor.return_value is not NOT_SET:
                logger.debug(f"Return value is set to: {return_value_processor.return_value}")
                return True

            if interruption_handler.interrupted_or_killed:
                logger.debug("Interrupted")
                return True

            # Compute Next Completion
            logger.debug(f"Computing next completion assistance")
            completion_assistance = compute_next_step(chat, step_contexts, signals)
            logger.debug(f"Next completion assistance: {completion_assistance}")
            if not completion_assistance:
                return True

            # Pre-Step
            if step_contexts['step_context']['current_step'] > 1:
                separator = compute_separator(chat['markdown_chat'])
                if separator:
                    await signals.response.response.send_async(separator)

            # Step
            await completion_assistance.perform_completion(chat)

            # Post-Step
            # TODO: Add lifecycle/checkpoint here
        return False
