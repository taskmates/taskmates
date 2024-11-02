from typing import TypedDict, Any

from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.types import Chat
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.run import RUN, Run
from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.actions.markdown_completion_action import MarkdownCompletionAction
from taskmates.workflows.contexts.context import Context
from taskmates.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.workflows.daemons.return_value_daemon import ReturnValueDaemon
from taskmates.workflows.rules.max_steps_check import MaxStepsCheck
from taskmates.workflows.states.current_step import CurrentStep
from taskmates.workflows.states.interrupted import Interrupted
from taskmates.workflows.states.interrupted_or_killed import InterruptedOrKilled
from taskmates.workflows.states.markdown_chat import MarkdownChat
from taskmates.workflows.states.return_value import ReturnValue


class CompletionRunEnvironment(TypedDict):
    current_step: int
    max_steps: int


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
        return {
            "max_steps_check": MaxStepsCheck(),
            "current_step": CurrentStep(),
        }

    @fulfills(outcome="state")
    async def create_state(self) -> dict[str, Any]:
        return {
            "interrupted": Interrupted(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
            "markdown_chat": MarkdownChat()
        }

    @fulfills(outcome="context")
    async def create_context(self, markdown_chat) -> Context:
        caller_run = RUN.get()
        forked_context: Context = caller_run.context.copy()

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

    @fulfills(outcome="markdown_complete_steps")
    async def steps(self, markdown_chat: str) -> str:
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        markdown_complete_run = RUN.get()
        while True:
            result = await self.attempt_completion(markdown_chat)
            if result is None:
                break
            markdown_chat = result

        response_format = markdown_complete_run.context["runner_config"]["format"]
        response = markdown_complete_run.state["markdown_chat"].get()[response_format]
        return response

    @fulfills(outcome="completion")
    async def attempt_completion(self, markdown_chat: str):
        completion_run = RUN.get()
        completion_run.signals["current_step"].increment()
        chat = await self.get_markdown_chat(markdown_chat)
        next_completion = await self.compute_next_completion(chat)

        if not next_completion:
            if completion_run.signals["current_step"].get() == 1:
                raise ValueError("No available completion")

            await self.end_workflow(chat, completion_run.context, completion_run)
            return None

        step = MarkdownCompletionAction()
        await step.perform(chat, next_completion)

        return completion_run.state["markdown_chat"].get()["full"]

    async def compute_next_completion(self, chat):
        run = RUN.get()
        should_break = False

        if run.signals["max_steps_check"].should_break():
            should_break = True

        if run.state["return_value"].get() is not NOT_SET:
            logger.debug(f"Return value is set to: {run.state['return_value'].get()}")
            should_break = True

        if run.state["interrupted_or_killed"].get():
            logger.debug("Interrupted")
            should_break = True

        if should_break:
            return None

        logger.debug(f"Computing next completion")
        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    @typechecked
    async def get_markdown_chat(self, markdown_chat: str):
        run: Run[Context] = RUN.get()
        chat: Chat = await parse_markdown_chat(
            markdown_chat=markdown_chat,
            markdown_path=(run.context["runner_environment"]["markdown_path"]),
            taskmates_dirs=(run.context["runner_config"]["taskmates_dirs"]),
            inputs=run.objective.inputs)
        return chat

    async def end_workflow(self, chat: Chat, contexts: Context, run: Run[Context]):
        logger.debug(f"Finished completion assistance")
        separator = compute_separator(chat["markdown_chat"])
        if separator:
            await run.signals["output_streams"].formatting.send_async(separator)
        if (contexts['runner_config']["interactive"] and
                not run.state["interrupted_or_killed"].get()):
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await run.signals["output_streams"].next_responder.send_async(f"**{recipient}>** ")
        await run.signals["status"].success.send_async({})
