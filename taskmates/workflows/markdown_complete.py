from typing import TypedDict

from typeguard import typechecked

from taskmates.actions.parse_markdown_chat import parse_markdown_chat
from taskmates.core.completion_provider import CompletionProvider
from taskmates.core.compute_next_completion import compute_next_completion
from taskmates.core.compute_separator import compute_separator
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger, file_logger
from taskmates.types import Chat
from taskmates.workflow_engine.base_signals import connected_signals
from taskmates.workflow_engine.environment_signals import EnvironmentSignals
from taskmates.workflow_engine.fulfills import fulfills
from taskmates.workflow_engine.run import RUN, Run, Objective, ObjectiveKey
from taskmates.workflow_engine.workflow import Workflow
from taskmates.workflows.actions.markdown_completion_step_action import MarkdownCompleteSectionAction
from taskmates.workflows.contexts.run_context import RunContext
from taskmates.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.workflows.daemons.markdown_completion_to_execution_environment_stdout_daemon import \
    MarkdownCompletionToExecutionEnvironmentStdoutDaemon
from taskmates.workflows.daemons.return_value_daemon import ReturnValueDaemon
from taskmates.workflows.rules.max_steps_check import MaxStepsCheck
from taskmates.workflows.signals.chat_completion_signals import ChatCompletionSignals
from taskmates.workflows.signals.code_cell_output_signals import CodeCellOutputSignals
from taskmates.workflows.signals.control_signals import ControlSignals
from taskmates.workflows.signals.input_streams import InputStreams
from taskmates.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.workflows.signals.status_signals import StatusSignals
from taskmates.workflows.states.current_step import CurrentStep
from taskmates.workflows.states.interrupted import Interrupted
from taskmates.workflows.states.interrupted_or_killed import InterruptedOrKilled
from taskmates.workflows.states.markdown_chat import MarkdownChat
from taskmates.workflows.states.return_value import ReturnValue


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


@typechecked
class MarkdownComplete(Workflow):
    def __init__(self):
        context = RUN.get().context.copy()
        daemons = {
            "markdown_completion_to_execution_environment_stdout":
                MarkdownCompletionToExecutionEnvironmentStdoutDaemon(),
            "interrupt_request_mediator": InterruptRequestDaemon(),
            "interrupted_or_killed": InterruptedOrKilledDaemon(),
            "return_value": ReturnValueDaemon(),
            "markdown_chat": MarkdownChatDaemon(),
        }
        signals = {
            'input_streams': InputStreams(),
        }
        state = {
            "interrupted": Interrupted(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
            "markdown_chat": MarkdownChat(),
            "current_step": CurrentStep(),
            "max_steps_check": MaxStepsCheck(),
        }
        super().__init__(context=context, daemons=daemons, signals=signals, state=state)

    async def steps(self, markdown_chat: str) -> str:
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        current_run = RUN.get()
        current_objective = current_run.objective
        context = current_run.context
        state = current_run.state
        parent_signals: EnvironmentSignals = current_run.signals

        await self.append_trailing_newlines(markdown_chat, parent_signals["markdown_completion"])

        step = 0
        while True:
            step += 1

            step_context = current_run.context.copy()
            step_run = Run(
                objective=Objective(
                    key=ObjectiveKey(
                        outcome=f"{current_objective.key['outcome']}-step-{step}",
                        inputs=current_objective.key.get("inputs"),
                        requesting_run=current_run
                    )
                ),
                context=step_context,
                signals={
                    "control": ControlSignals(),
                    "status": StatusSignals(),
                    "markdown_completion": MarkdownCompletionSignals(),
                    "chat_completion": ChatCompletionSignals(),
                    "code_cell_output": CodeCellOutputSignals(),
                },
                state=current_run.state,
                daemons={}
            )

            with (
                step_run,
                connected_signals([
                    (current_run.signals["control"], step_run.signals["control"]),
                    (step_run.signals["status"], current_run.signals["status"]),
                    (step_run.signals["markdown_completion"], current_run.signals["markdown_completion"]),
                    (step_run.signals["chat_completion"], current_run.signals["chat_completion"]),
                    (step_run.signals["code_cell_output"], current_run.signals["code_cell_output"])
                ]),
            ):
                should_continue = await self.complete_section(markdown_chat,
                                                              step_run.state,
                                                              step_run.signals)
                markdown_chat = state["markdown_chat"].get()["full"]
                if not should_continue:
                    break

        await self.end_markdown_completion(
            markdown_chat=markdown_chat,
            context=current_run.context,
            markdown_completion=current_run.signals["markdown_completion"],
            status=current_run.signals["status"],
            interrupted_or_killed=current_run.state["interrupted_or_killed"]
        )

        response_format = context["runner_config"]["format"]
        response = state["markdown_chat"].get()[response_format]
        return response

    @fulfills(outcome="markdown_section_completion")
    async def complete_section(self,
                               markdown_chat: str,
                               state: dict,
                               completion_signals: EnvironmentSignals):
        state["current_step"].increment()

        chat = await self.get_markdown_chat(markdown_chat)
        file_logger.debug("parsed_chat.json", content=chat)

        next_completion = await self.compute_next_completion(chat)
        if not next_completion:
            return False

        step = MarkdownCompleteSectionAction()
        await step.perform(chat,
                           next_completion,
                           completion_signals["control"],
                           completion_signals["markdown_completion"],
                           completion_signals["chat_completion"],
                           completion_signals["code_cell_output"],
                           completion_signals["status"])

        await self.end_section(state, completion_signals["markdown_completion"])

        return True

    async def compute_next_completion(self, chat):
        finished = await self.check_is_finished()

        if finished:
            return None

        completion_assistance = compute_next_completion(chat)
        logger.debug(f"Next completion: {completion_assistance}")

        return completion_assistance

    async def check_is_finished(self):
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

    async def get_markdown_chat(self, markdown_chat: str):
        run: Run = RUN.get()
        chat: Chat = await parse_markdown_chat(
            markdown_chat=markdown_chat,
            markdown_path=(run.context["runner_environment"]["markdown_path"]),
            taskmates_dirs=(run.context["runner_config"]["taskmates_dirs"]),
            inputs=run.objective.key['inputs'])
        return chat

    async def end_section(self, state, markdown_completion_signals: MarkdownCompletionSignals):
        markdown_completion = state["markdown_chat"].outputs["completion"]
        await self.append_trailing_newlines(markdown_completion, markdown_completion_signals)

    async def end_markdown_completion(self,
                                      markdown_chat: str,
                                      context: RunContext,
                                      markdown_completion: MarkdownCompletionSignals,
                                      status: StatusSignals,
                                      interrupted_or_killed: InterruptedOrKilled):
        chat = await self.get_markdown_chat(markdown_chat)

        if CompletionProvider.has_truncated_code_cell(chat):
            logger.debug(f"Truncated completion assistance")
            return

        await self.append_next_responder(
            chat=chat,
            context=context,
            markdown_completion=markdown_completion,
            interrupted_or_killed=interrupted_or_killed
        )

        await status.success.send_async({})
        logger.debug(f"Finished completion assistance")

    async def append_next_responder(self,
                                    chat: Chat,
                                    context: RunContext,
                                    markdown_completion: MarkdownCompletionSignals,
                                    interrupted_or_killed: InterruptedOrKilled):
        if context['runner_config']["interactive"] and not interrupted_or_killed.get():
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await markdown_completion.next_responder.send_async(f"**{recipient}>** ")

    async def append_trailing_newlines(self, markdown_chat: str, markdown_completion: MarkdownCompletionSignals):
        chat = await self.get_markdown_chat(markdown_chat)

        if CompletionProvider.has_truncated_code_cell(chat):
            return

        separator = compute_separator(markdown_chat)
        if separator:
            await markdown_completion.formatting.send_async(separator)
