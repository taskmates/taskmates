from typing import TypedDict

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.completion_provider import CompletionProvider
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.types import Chat
from taskmates.workflow_engine.environment_signals import EnvironmentSignals
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.run import RUN, Run
from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.actions.markdown_completion_step_action import MarkdownCompleteSectionAction
from taskmates.workflows.contexts.run_context import RunContext
from taskmates.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.workflows.daemons.return_value_daemon import ReturnValueDaemon
from taskmates.workflows.rules.max_steps_check import MaxStepsCheck
from taskmates.workflows.signals.output_streams import OutputStreams
from taskmates.workflows.states.current_step import CurrentStep
from taskmates.workflows.states.interrupted import Interrupted
from taskmates.workflows.states.interrupted_or_killed import InterruptedOrKilled
from taskmates.workflows.states.markdown_chat import MarkdownChat
from taskmates.workflows.states.return_value import ReturnValue
from typeguard import typechecked


class CompletionRunEnvironment(TypedDict):
    current_step: int
    max_steps: int


class MarkdownCompleteState(TypedDict):
    interrupted: Interrupted
    interrupted_or_killed: InterruptedOrKilled
    return_value: ReturnValue
    markdown_chat: MarkdownChat
    current_step: CurrentStep
    max_steps_check: MaxStepsCheck


class MarkdownComplete(Workflow):
    def __init__(self):
        super().__init__()

    @fulfills(outcome="daemons")
    async def create_daemons(self):
        return {
            "interrupt_request_mediator": InterruptRequestDaemon(),
            "interrupted_or_killed": InterruptedOrKilledDaemon(),
            "return_value": ReturnValueDaemon(),
            "markdown_chat": MarkdownChatDaemon(),
        }

    @fulfills(outcome="signals")
    async def create_signals(self):
        return {}

    @fulfills(outcome="state")
    async def create_state(self) -> MarkdownCompleteState:
        return {
            "interrupted": Interrupted(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
            "markdown_chat": MarkdownChat(),
            "current_step": CurrentStep(),
            "max_steps_check": MaxStepsCheck(),
        }

    @fulfills(outcome="context")
    async def create_context(self, markdown_chat) -> RunContext:
        caller_run = RUN.get()
        forked_context: RunContext = caller_run.context.copy()

        caller_run_opts = forked_context["run_opts"]

        incoming_markdown = markdown_chat
        chat = await self.get_markdown_chat(incoming_markdown)
        chat_run_opts = chat["run_opts"]

        updated_run_opts = {**caller_run_opts, **chat_run_opts}
        computed_run_opts = {}
        if updated_run_opts["model"] in ("quote", "echo"):
            computed_run_opts["max_steps"] = 1

        updated_run_opts = {**caller_run_opts, **chat_run_opts, **computed_run_opts}

        forked_context["run_opts"].update(updated_run_opts)

        return forked_context

    @fulfills(outcome="markdown_completion")
    async def steps(self, markdown_chat: str) -> str:
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        current_run = RUN.get()
        context = current_run.context
        state = current_run.state
        output_streams: OutputStreams = current_run.signals["output_streams"]

        await self.append_trailing_newlines(markdown_chat, output_streams)
        # current_run.objective.print_graph()

        while True:
            parent_signals: EnvironmentSignals = current_run.signals
            # completion_signals = fork_signals(parent_signals)
            completion_signals = parent_signals

            markdown_section_completion = await self.complete_section(markdown_chat, completion_signals)
            if not markdown_section_completion:
                break
            markdown_chat = state["markdown_chat"].get()["full"]
            await self.on_after_step()

        response_format = context["runner_config"]["format"]
        response = state["markdown_chat"].get()[response_format]
        return response

    # TODO outcome hooks?
    @fulfills(outcome="markdown_section_completion")
    async def complete_section(self, markdown_chat: str, completion_signals: EnvironmentSignals):
        current_run = RUN.get()
        output_streams = completion_signals["output_streams"]

        state = current_run.state
        state["current_step"].increment()

        chat = await self.get_markdown_chat(markdown_chat)
        await output_streams.artifact.send_async({"name": "parsed_chat.json", "content": chat})

        next_completion = await self.compute_next_completion(chat)
        if not next_completion:
            await self.end_markdown_completion(chat, current_run.context, current_run)
            return False

        step = MarkdownCompleteSectionAction()
        await step.perform(chat, next_completion, completion_signals)

        # current_run.objective.print_graph()

        # TODO: return a rich result here
        return True

    async def on_after_step(self):
        run = RUN.get()
        state = run.state
        output_streams: OutputStreams = run.signals["output_streams"]

        chat = await self.get_markdown_chat(state["markdown_chat"].get()["full"])

        if CompletionProvider.has_truncated_code_cell(chat):
            return

        markdown_completion = run.state["markdown_chat"].outputs["completion"]
        await self.append_trailing_newlines(markdown_completion, output_streams)

    async def append_trailing_newlines(self, markdown_chat: str, output_streams: OutputStreams):
        separator = compute_separator(markdown_chat)
        if separator:
            await output_streams.formatting.send_async(separator)

    async def compute_next_completion(self, chat):
        finished = await self.check_finished()

        if finished:
            return None

        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    async def check_finished(self):
        run = RUN.get()
        finished = False
        if run.state["max_steps_check"].should_break():
            finished = True
        if run.state["return_value"].get() is not NOT_SET:
            logger.debug(f"Return value is set to: {run.state['return_value'].get()}")
            finished = True
        if run.state["interrupted_or_killed"].get():
            logger.debug("Interrupted")
            finished = True
        return finished

    @typechecked
    async def get_markdown_chat(self, markdown_chat: str):
        run: Run = RUN.get()
        chat: Chat = await parse_markdown_chat(
            markdown_chat=markdown_chat,
            markdown_path=(run.context["runner_environment"]["markdown_path"]),
            taskmates_dirs=(run.context["runner_config"]["taskmates_dirs"]),
            inputs=run.objective.key['inputs'])
        return chat

    async def end_markdown_completion(self, chat: Chat, contexts: RunContext, run: Run):
        if CompletionProvider.has_truncated_code_cell(chat):
            logger.debug(f"Truncated completion assistance")
            return

        await self.append_next_responder(chat, contexts, run)
        await run.signals["status"].success.send_async({})
        logger.debug(f"Finished completion assistance")

    async def append_next_responder(self, chat, contexts, run):
        if (contexts['runner_config']["interactive"] and
                not run.state["interrupted_or_killed"].get()):
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await run.signals["output_streams"].next_responder.send_async(f"**{recipient}>** ")
