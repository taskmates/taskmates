from typing import TypedDict

from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.core.daemons.interrupt_request_mediator import InterruptRequestMediator
from taskmates.core.daemons.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.daemons.return_value import ReturnValue
from taskmates.core.io.listeners.markdown_chat import MarkdownChat
from taskmates.core.rules.max_steps_check import MaxStepsCheck
from taskmates.core.run import RUN, Run
from taskmates.core.states.current_step import CurrentStep
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.runner.actions.markdown_completion_action import MarkdownCompletionAction
from taskmates.runner.contexts.runner_context import RunnerContext
from taskmates.types import Chat


class MarkdownCompleteState(TypedDict):
    max_steps_check: MaxStepsCheck
    current_step_update: CurrentStep


class MarkdownComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: RunnerContext = None
                 ):

        super().__init__(contexts=contexts,
                         jobs={
                             "interrupt_request_mediator": InterruptRequestMediator(),
                             "interrupted_or_killed": InterruptedOrKilled(),
                             "return_value": ReturnValue(),
                             "markdown_chat": MarkdownChat(),
                         })
        # TODO:
        # self.outputs
        # self.topics

    @typechecked
    async def run(self, markdown_chat: str) -> str:
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        contexts = RUN.get().contexts
        run = RUN.get()

        response_format = contexts["runner_config"]["format"]

        await self.start_workflow(run)

        # Update state
        updated_markdown = run.jobs_registry["markdown_chat"].get()["full"]
        chat = await self.get_markdown_chat(updated_markdown, contexts)

        job_state: MarkdownCompleteState = {
            # TODO: markdown workflow step/state
            "max_steps_check": MaxStepsCheck(),
            # TODO: markdown workflow step/state -> completion job input
            "current_step_update": CurrentStep(),
        }

        await self.prepare_completion_job_context(chat, contexts)

        while True:
            with Run():
                await self.prepare_step_context(job_state, chat, contexts)

                next_completion = await self.compute_next_completion(job_state, chat)

                if not next_completion:
                    if contexts["step_context"]["current_step"] == 1:
                        raise ValueError("No available completion")

                    run = RUN.get()
                    await self.end_workflow(chat, contexts, run)

                    response = run.jobs_registry["markdown_chat"].get()[response_format]
                    return response

                step = MarkdownCompletionAction()
                await step.perform(chat, next_completion)

                # Update state
                updated_markdown = run.jobs_registry["markdown_chat"].get()["full"]
                chat = await self.get_markdown_chat(updated_markdown, contexts)

    async def compute_next_completion(self, run_state, chat):
        run = RUN.get()
        contexts = run.contexts

        should_break = False

        if run_state["max_steps_check"].should_break(contexts):
            should_break = True

        if run.jobs_registry["return_value"].get() is not NOT_SET:
            logger.debug(f"Return value is set to: {run_state['return_value'].get()}")
            should_break = True

        if run.jobs_registry["interrupted_or_killed"].get():
            logger.debug("Interrupted")
            should_break = True

        if should_break:
            return None

        logger.debug(f"Computing next completion")
        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    async def prepare_step_context(self, run_state, chat: Chat, contexts: RunnerContext):
        run_state["current_step_update"].increment()
        current_step = run_state["current_step_update"].get()
        contexts['step_context']['current_step'] = current_step
        return chat

    async def prepare_completion_job_context(self, chat: Chat, contexts: RunnerContext):
        contexts["run_opts"].update(chat["run_opts"])

        if "model" in chat["run_opts"]:
            contexts['run_opts']["model"] = chat["run_opts"]["model"]
        if contexts['run_opts']["model"] in ("quote", "echo"):
            contexts['run_opts']["max_steps"] = 1
        return chat

    @typechecked
    async def get_markdown_chat(self, markdown_chat: str, contexts: RunnerContext):
        chat: Chat = await parse_markdown_chat(
            markdown_chat=markdown_chat,
            markdown_path=(contexts["runner_environment"]["markdown_path"]),
            taskmates_dirs=(contexts["runner_config"]["taskmates_dirs"]),
            inputs=(contexts["run_opts"]["inputs"]))
        return chat

    async def start_workflow(self, signals):
        await signals.status.start.send_async({})

    async def end_workflow(self, chat: Chat, contexts: RunnerContext, run: Run):
        logger.debug(f"Finished completion assistance")
        separator = compute_separator(chat["markdown_chat"])
        if separator:
            await run.output_streams.formatting.send_async(separator)
        if (contexts['runner_config']["interactive"] and
                not run.jobs_registry["interrupted_or_killed"].get()):
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await run.output_streams.next_responder.send_async(f"**{recipient}>** ")
        await run.status.success.send_async({})
