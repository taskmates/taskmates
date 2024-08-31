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
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector
from taskmates.signals.signals import Signals, SIGNALS
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
        self.contexts = contexts
        self.signals = signals
        self.handlers = handlers
        self.states = {
            "current_markdown": CurrentMarkdown(),
        }

    async def resume(self):
        history = self.history
        incoming_messages = self.incoming_messages

        handlers = self.handlers
        contexts = self.contexts
        signals = self.signals
        states = {
            "current_step": CurrentStep(),
            "interrupted_or_killed": InterruptedOrKilledCollector(),
            "return_value": ReturnValueCollector(),
            "max_steps_manager": MaxStepsManager(),
            **self.states
        }

        # app scoped
        request_handlers = [*handlers,
                            states["current_markdown"],
                            IncomingMessagesFormattingProcessor(),
                            InterruptRequestCollector(),
                            states["interrupted_or_killed"],
                            states["return_value"]]

        with temp_context(CONTEXTS, copy.deepcopy(contexts)), \
                signals.connected_to(request_handlers):
            await self.handle_request(history, incoming_messages, states)

    async def handle_request(self, history, incoming_messages, states):
        contexts = CONTEXTS.get()
        signals = SIGNALS.get()
        interactive = contexts['client_config']["interactive"]
        # Input
        if history:
            await signals.input.history.send_async(history)
        for incoming_message in incoming_messages:
            if incoming_message:
                await signals.input.incoming_message.send_async(incoming_message)
        # Lifecycle: Start
        await signals.lifecycle.start.send_async({})
        markdown_path = contexts["completion_context"]["markdown_path"]
        taskmates_dirs = contexts["client_config"]["taskmates_dirs"]
        template_params = contexts["completion_opts"]["template_params"]
        while True:
            current_markdown = states["current_markdown"].get()

            chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                   markdown_path=markdown_path,
                                                   taskmates_dirs=taskmates_dirs,
                                                   template_params=template_params)

            # Pre-Step
            states["current_step"].increment()

            with temp_context(CONTEXTS, copy.deepcopy(contexts)):
                CONTEXTS.get()["completion_opts"].update(chat["completion_opts"])
                should_break = await self.perform_step(chat, states)

                if should_break:
                    break
        logger.debug(f"Finished completion assistance")
        # TODO: Add lifecycle/checkpoint here
        # TODO reload from file system
        separator = compute_separator(states["current_markdown"].get())
        if separator:
            await signals.response.formatting.send_async(separator)
        # Post-Completion
        if interactive and not states["interrupted_or_killed"].interrupted_or_killed:
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await signals.response.next_responder.send_async(f"**{recipient}>** ")
        # Lifecycle: Success
        await signals.lifecycle.success.send_async({})

    async def perform_step(self, chat: Chat, states):
        contexts = CONTEXTS.get()
        signals = SIGNALS.get()

        # Enrich context
        contexts['step_context']['current_step'] = states["current_step"].get()

        if "model" in chat["completion_opts"]:
            contexts['completion_opts']["model"] = chat["completion_opts"]["model"]

        if contexts['completion_opts']["model"] in ("quote", "echo"):
            contexts['completion_opts']["max_steps"] = 1

        # Guards
        if states["max_steps_manager"].should_break(contexts):
            return True

        if states["return_value"].return_value is not NOT_SET:
            logger.debug(f"Return value is set to: {states['return_value'].return_value}")
            return True

        if states["interrupted_or_killed"].interrupted_or_killed:
            logger.debug("Interrupted")
            return True

            # Compute Next Completion
        logger.debug(f"Computing next completion assistance")
        completion_assistance = compute_next_step(chat)
        logger.debug(f"Next completion assistance: {completion_assistance}")
        if not completion_assistance:
            return True

        # Pre-Step
        if contexts['step_context']['current_step'] > 1:
            separator = compute_separator(chat['markdown_chat'])
            if separator:
                await signals.response.response.send_async(separator)

        # Step
        await completion_assistance.perform_completion(chat)

        # Post-Step
        # TODO: Add lifecycle/checkpoint here
        return False
