from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.config.client_config import ClientConfig
from taskmates.config.completion_context import CompletionContext
from taskmates.config.completion_opts import CompletionOpts
from taskmates.config.server_config import ServerConfig
from taskmates.core.completion_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.logging import logger
from taskmates.signals.signals import Signals
from taskmates.types import Chat


class FullMarkdownCollector:
    def __init__(self):
        self.markdown_chunks = []

    async def handle(self, markdown):
        if markdown is not None:
            self.markdown_chunks.append(markdown)

    def get_current_markdown(self):
        return "".join(self.markdown_chunks)

    def connect(self, signals):
        signals.input.input.connect(self.handle, weak=False)
        signals.response.formatting.connect(self.handle, weak=False)
        signals.response.response.connect(self.handle, weak=False)
        signals.response.responder.connect(self.handle, weak=False)
        signals.response.error.connect(self.handle, weak=False)

    def disconnect(self, signals):
        signals.input.input.connect(self.handle, weak=False)
        signals.response.formatting.connect(self.handle, weak=False)
        signals.response.response.connect(self.handle, weak=False)
        signals.response.responder.connect(self.handle, weak=False)
        signals.response.error.connect(self.handle, weak=False)


class ReturnValueProcessor:
    def __init__(self):
        self.return_value = None

    async def handle_return_value(self, status):
        logger.debug(f"Return status: {status}")
        self.return_value = status

    def connect(self, signals):
        signals.output.return_value.connect(self.handle_return_value)

    def disconnect(self, signals):
        signals.output.return_value.disconnect(self.handle_return_value)


class InterruptedOrKilledHandler:
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


class InterruptRequestHandler:
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


class CompletionEngine:
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

        markdown_collector = FullMarkdownCollector()
        return_value_processor = ReturnValueProcessor()
        interruption_handler = InterruptedOrKilledHandler()
        interrupt_request_handler = InterruptRequestHandler(signals)

        with signals.connected_to(
                [markdown_collector,
                 interrupt_request_handler,
                 interruption_handler,
                 return_value_processor]):

            await signals.input.input.send_async(markdown_chat)

            separator = compute_separator(markdown_chat)
            if separator:
                await signals.response.formatting.send_async(separator)

            await signals.lifecycle.start.send_async({})

            current_interaction = 0
            max_interactions = completion_opts["max_interactions"]
            while True:
                current_markdown = markdown_collector.get_current_markdown()

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
                completion_assistance = compute_next_completion(chat)

                logger.debug(f"Next completion assistance: {completion_assistance}")
                if not completion_assistance:
                    break

                current_interaction += 1

                if current_interaction > max_interactions:
                    break

                if current_interaction > 1:
                    separator = compute_separator(current_markdown)
                    if separator:
                        await signals.response.response.send_async(separator)

                # NOTE: Completion

                await completion_assistance.perform_completion(context, chat, signals)

                if return_value_processor.return_value is not None:
                    logger.debug(f"Return status is not None: {return_value_processor.return_value}")
                    break

                if interruption_handler.interrupted_or_killed:
                    logger.debug("Interrupted")
                    break

            logger.debug(f"Finished completion assistance")

            if interactive and not interruption_handler.interrupted_or_killed:
                separator = compute_separator(markdown_collector.get_current_markdown())
                if separator:
                    await signals.response.next_responder.send_async(separator)

                recipient = chat["messages"][-1]["recipient"]
                if recipient:
                    await signals.response.next_responder.send_async(f"**{recipient}>** ")

            await signals.lifecycle.success.send_async({})
