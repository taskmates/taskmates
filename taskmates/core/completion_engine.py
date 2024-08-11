from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.contexts import Contexts
from taskmates.core.completion_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.io.formatting_processor import IncomingMessagesFormattingProcessor
from taskmates.logging import logger
from taskmates.signals.handler import Handler
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
        client_config = contexts['client_config']
        completion_opts = contexts['completion_opts']

        taskmates_dirs = completion_opts.get("taskmates_dirs")
        interactive = client_config["interactive"]

        markdown_collector = FullMarkdownCollector()
        incoming_messages_formatting_processor = IncomingMessagesFormattingProcessor(signals)
        return_value_processor = ResultProcessor()
        interruption_handler = InterruptedOrKilledHandler()
        interrupt_request_handler = InterruptRequestHandler(signals)

        with signals.connected_to(
                [markdown_collector,
                 incoming_messages_formatting_processor,
                 interrupt_request_handler,
                 interruption_handler,
                 return_value_processor]):

            # TODO think about remote control
            # TODO think about history saving

            # Input
            if history:
                await signals.input.history.send_async(history)

            for incoming_message in incoming_messages:
                if incoming_message:
                    await signals.input.incoming_message.send_async(incoming_message)

            # Lifecycle: Start
            await signals.lifecycle.start.send_async({})

            current_interaction = 0
            while True:
                current_markdown = markdown_collector.get_current_markdown()

                logger.debug(f"Parsing markdown chat")
                chat: Chat = await parse_markdown_chat(markdown_chat=current_markdown,
                                                       markdown_path=contexts["completion_context"]["markdown_path"],
                                                       taskmates_dirs=taskmates_dirs,
                                                       template_params=completion_opts["template_params"])

                if "model" in chat["metadata"]:
                    completion_opts["model"] = chat["metadata"]["model"]

                if completion_opts["model"] in ("quote", "echo"):
                    completion_opts["max_interactions"] = 1

                logger.debug(f"Computing next completion assistance")
                completion_assistance = compute_next_completion(chat, completion_opts)

                logger.debug(f"Next completion assistance: {completion_assistance}")
                if not completion_assistance:
                    break

                # Pre-Step

                current_interaction += 1

                if current_interaction > completion_opts["max_interactions"]:
                    break

                if current_interaction > 1:
                    separator = compute_separator(current_markdown)
                    if separator:
                        await signals.response.response.send_async(separator)

                # TODO: compute env here

                # Step
                await completion_assistance.perform_completion(chat, contexts, signals)

                # TODO: Add lifecycle/checkpoint here

                # Post-Step
                if return_value_processor.result is not None:
                    logger.debug(f"Return status is not None: {return_value_processor.result}")
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


class FullMarkdownCollector(Handler):
    def __init__(self):
        self.markdown_chunks = []

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get_current_markdown(self):
        return "".join(self.markdown_chunks)

    def connect(self, signals):
        signals.input.history.connect(self.handle, weak=False)
        signals.input.incoming_message.connect(self.handle, weak=False)
        signals.input.formatting.connect(self.handle, weak=False)
        signals.response.formatting.connect(self.handle, weak=False)
        signals.response.response.connect(self.handle, weak=False)
        signals.response.responder.connect(self.handle, weak=False)
        signals.response.error.connect(self.handle, weak=False)

    def disconnect(self, signals):
        signals.input.history.disconnect(self.handle)
        signals.input.incoming_message.disconnect(self.handle)
        signals.input.formatting.disconnect(self.handle)
        signals.response.formatting.disconnect(self.handle)
        signals.response.response.disconnect(self.handle)
        signals.response.responder.disconnect(self.handle)
        signals.response.error.disconnect(self.handle)


# TODO: move return logic here
class ResultProcessor(Handler):
    def __init__(self):
        self.result = None

    async def handle_result(self, result):
        logger.debug(f"Result: {result}")
        self.result = result

    def connect(self, signals):
        signals.output.result.connect(self.handle_result)

    def disconnect(self, signals):
        signals.output.result.disconnect(self.handle_result)


# TODO: move interruption logic here
class InterruptedOrKilledHandler(Handler):
    def __init__(self):
        self.interrupted_or_killed = False

    async def handle_interrupted(self, _sender):
        self.interrupted_or_killed = True

    async def handle_killed(self, _sender):
        self.interrupted_or_killed = True

    def connect(self, signals):
        signals.lifecycle.interrupted.connect(self.handle_interrupted)
        signals.lifecycle.killed.connect(self.handle_killed)

    def disconnect(self, signals):
        signals.lifecycle.interrupted.disconnect(self.handle_interrupted)
        signals.lifecycle.killed.disconnect(self.handle_killed)


class InterruptRequestHandler(Handler):
    def __init__(self, signals):
        self.interrupt_requested = False
        self.signals = signals

    async def handle_interrupt_request(self, _sender):
        if self.interrupt_requested:
            logger.info("Interrupt requested again. Killing the request.")
            await self.signals.control.kill.send_async({})
        else:
            logger.info("Interrupt requested")
            await self.signals.control.interrupt.send_async({})
            self.interrupt_requested = True

    def connect(self, signals):
        signals.control.interrupt_request.connect(self.handle_interrupt_request)

    def disconnect(self, signals):
        signals.control.interrupt_request.disconnect(self.handle_interrupt_request)
