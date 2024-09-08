import copy

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.core.signal_receivers.current_markdown import CurrentMarkdown
from taskmates.core.signal_receivers.current_step import CurrentStep
from taskmates.core.signal_receivers.interrupt_request_collector import InterruptRequestCollector
from taskmates.core.signal_receivers.interrupted_or_killed_collector import InterruptedOrKilledCollector
from taskmates.core.signal_receivers.max_steps_manager import MaxStepsManager
from taskmates.core.signals import SIGNALS, Signals
from taskmates.core.states import WorkflowState
from taskmates.lib.context_.temp_context import temp_context
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger
from taskmates.runner.actions.markdown_completion_action import MarkdownCompletionAction
from taskmates.runner.contexts.contexts import CONTEXTS, Contexts
from taskmates.defaults.workflows.taskmates_workflow import TaskmatesWorkflow
from taskmates.sdk.handlers.return_value_collector import ReturnValueCollector
from taskmates.types import Chat


class MarkdownComplete(TaskmatesWorkflow):
    async def run(self, current_markdown: str) -> str:
        run_state: WorkflowState = {
            "interrupted_or_killed": InterruptedOrKilledCollector(),
            "return_value": ReturnValueCollector(),
            "max_steps_manager": MaxStepsManager(),
            "current_step": CurrentStep(),
            "current_markdown": CurrentMarkdown(current_markdown),
        }

        contexts = CONTEXTS.get()
        signals = SIGNALS.get()

        request_handlers = [run_state["current_markdown"],
                            InterruptRequestCollector(),
                            run_state["interrupted_or_killed"],
                            run_state["return_value"]]

        with temp_context(CONTEXTS, copy.deepcopy(contexts)), \
                signals.connected_to(request_handlers):

            contexts = CONTEXTS.get()
            signals = SIGNALS.get()

            await self.start_workflow(signals)

            # Update state
            chat = await self.update_job_state(run_state, contexts)

            await self.prepare_job_context(chat, contexts)

            while True:
                with temp_context(CONTEXTS, copy.deepcopy(contexts)):

                    await self.prepare_step_context(run_state, chat, contexts)

                    next_completion = await self.compute_next_completion(run_state, chat)

                    if not next_completion:
                        await self.end_workflow(run_state, chat, contexts, signals)
                        return chat["markdown_chat"]

                    step = MarkdownCompletionAction()
                    await step.perform(chat, next_completion)

                    # Update state
                    chat = await self.update_job_state(run_state, contexts)

    async def compute_next_completion(self, run_state, chat):
        contexts = CONTEXTS.get()

        should_break = False

        if run_state["max_steps_manager"].should_break(contexts):
            should_break = True

        if run_state["return_value"].return_value is not NOT_SET:
            logger.debug(f"Return value is set to: {run_state['return_value'].return_value}")
            should_break = True

        if run_state["interrupted_or_killed"].interrupted_or_killed:
            logger.debug("Interrupted")
            should_break = True

        if should_break:
            return None

        logger.debug(f"Computing next completion")
        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    async def prepare_step_context(self, run_state, chat: Chat, contexts: Contexts):
        run_state["current_step"].increment()
        current_step = run_state["current_step"].get()
        contexts['step_context']['current_step'] = current_step
        return chat

    async def prepare_job_context(self, chat: Chat, contexts: Contexts):
        contexts["completion_opts"].update(chat["completion_opts"])

        if "model" in chat["completion_opts"]:
            contexts['completion_opts']["model"] = chat["completion_opts"]["model"]
        if contexts['completion_opts']["model"] in ("quote", "echo"):
            contexts['completion_opts']["max_steps"] = 1
        return chat

    async def update_job_state(self, run_state, contexts):
        current_markdown = run_state["current_markdown"].get()
        chat: Chat = await parse_markdown_chat(
            markdown_chat=current_markdown,
            markdown_path=(contexts["completion_context"]["markdown_path"]),
            taskmates_dirs=(contexts["client_config"]["taskmates_dirs"]),
            inputs=(contexts["completion_opts"]["inputs"]))
        return chat

    async def start_workflow(self, signals):
        await signals.lifecycle.start.send_async({})

    async def end_workflow(self, run_state, chat: Chat, contexts: Contexts, signals: Signals):
        logger.debug(f"Finished completion assistance")
        separator = compute_separator(chat["markdown_chat"])
        if separator:
            await signals.response.formatting.send_async(separator)
        if (contexts['client_config']["interactive"] and
                not run_state["interrupted_or_killed"].interrupted_or_killed):
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await signals.response.next_responder.send_async(f"**{recipient}>** ")
        await signals.lifecycle.success.send_async({})