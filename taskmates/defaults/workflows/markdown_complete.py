from typing import TypedDict

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.core.execution_context import EXECUTION_CONTEXT, merge_jobs, ExecutionContext
from taskmates.core.io.listeners.markdown_chat import MarkdownChat
from taskmates.core.rules.max_steps_check import MaxStepsCheck
from taskmates.core.states.current_step import CurrentStep
from taskmates.core.taskmates_workflow import TaskmatesWorkflow
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.runner.actions.markdown_completion_action import MarkdownCompletionAction
from taskmates.runner.contexts.contexts import Contexts
from taskmates.types import Chat


class MarkdownCompleteState(TypedDict):
    max_steps_check: MaxStepsCheck
    current_step_update: CurrentStep


class MarkdownComplete(TaskmatesWorkflow):
    def __init__(self, *,
                 contexts: Contexts = None,
                 jobs: dict[str, ExecutionContext] | list[ExecutionContext] = None,
                 inputs: dict = None,
                 ):
        self.markdown_chat = MarkdownChat()
        super().__init__(contexts=contexts,
                         jobs=merge_jobs(jobs, {
                             "markdown_chat": self.markdown_chat,
                         }),
                         inputs=inputs)

    async def run(self, markdown_chat: str) -> str:
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        contexts = EXECUTION_CONTEXT.get().contexts
        execution_context = EXECUTION_CONTEXT.get()

        await self.start_workflow(execution_context)

        # Update state
        updated_markdown = self.jobs_registry["markdown_chat"].get()
        chat = await self.get_markdown_chat(updated_markdown, contexts)

        job_state: MarkdownCompleteState = {
            # TODO: markdown workflow step/state
            "max_steps_check": MaxStepsCheck(),
            # TODO: markdown workflow step/state -> completion job input
            "current_step_update": CurrentStep(),
        }

        await self.prepare_job_context(chat, contexts)

        while True:
            with ExecutionContext():
                await self.prepare_step_context(job_state, chat, contexts)

                next_completion = await self.compute_next_completion(job_state, chat)

                if not next_completion:
                    if contexts["step_context"]["current_step"] == 1:
                        raise ValueError("No available completion")

                    await self.end_workflow(chat, contexts, execution_context)
                    return chat["markdown_chat"]

                step = MarkdownCompletionAction()
                await step.perform(chat, next_completion)

                # Update state
                updated_markdown = self.jobs_registry["markdown_chat"].get()
                chat = await self.get_markdown_chat(updated_markdown, contexts)

    async def compute_next_completion(self, run_state, chat):
        contexts = EXECUTION_CONTEXT.get().contexts

        should_break = False

        if run_state["max_steps_check"].should_break(contexts):
            should_break = True

        if self.execution_context.jobs_registry["return_value"].get() is not NOT_SET:
            logger.debug(f"Return value is set to: {run_state['return_value'].get()}")
            should_break = True

        if self.execution_context.jobs_registry["interrupted_or_killed"].get():
            logger.debug("Interrupted")
            should_break = True

        if should_break:
            return None

        logger.debug(f"Computing next completion")
        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    async def prepare_step_context(self, run_state, chat: Chat, contexts: Contexts):
        run_state["current_step_update"].increment()
        current_step = run_state["current_step_update"].get()
        contexts['step_context']['current_step'] = current_step
        return chat

    async def prepare_job_context(self, chat: Chat, contexts: Contexts):
        contexts["completion_opts"].update(chat["completion_opts"])

        if "model" in chat["completion_opts"]:
            contexts['completion_opts']["model"] = chat["completion_opts"]["model"]
        if contexts['completion_opts']["model"] in ("quote", "echo"):
            contexts['completion_opts']["max_steps"] = 1
        return chat

    async def get_markdown_chat(self, markdown_chat, contexts):
        chat: Chat = await parse_markdown_chat(
            markdown_chat=markdown_chat,
            markdown_path=(contexts["completion_context"]["markdown_path"]),
            taskmates_dirs=(contexts["client_config"]["taskmates_dirs"]),
            inputs=(contexts["completion_opts"]["inputs"]))
        return chat

    async def start_workflow(self, signals):
        await signals.status.start.send_async({})

    async def end_workflow(self, chat: Chat, contexts: Contexts, execution_context: ExecutionContext):
        logger.debug(f"Finished completion assistance")
        separator = compute_separator(chat["markdown_chat"])
        if separator:
            await execution_context.output_streams.formatting.send_async(separator)
        if (contexts['client_config']["interactive"] and
                not self.execution_context.jobs_registry["interrupted_or_killed"].get()):
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await execution_context.output_streams.next_responder.send_async(f"**{recipient}>** ")
        await execution_context.status.success.send_async({})
