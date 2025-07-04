import pytest
from typeguard import typechecked

from taskmates.core.markdown_chat.compute_separator import compute_separator
from taskmates.core.markdown_chat.parse_markdown_chat import parse_markdown_chat
from taskmates.core.workflow_engine.base_signals import connected_signals
from taskmates.core.workflow_engine.environment_signals import EnvironmentSignals
from taskmates.core.workflow_engine.fulfills import fulfills
from taskmates.core.workflow_engine.run import RUN, Run, Objective, ObjectiveKey
from taskmates.core.workflow_engine.run_context import RunContext
from taskmates.core.workflow_engine.workflow import Workflow
from taskmates.core.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.core.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.core.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.core.workflows.daemons.markdown_completion_to_execution_environment_stdout_daemon import \
    MarkdownCompletionToExecutionEnvironmentStdoutDaemon
from taskmates.core.workflows.daemons.return_value_daemon import ReturnValueDaemon
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.compute_next_completion import compute_next_completion
from taskmates.core.workflows.markdown_completion.max_steps_check import MaxStepsCheck
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.input_streams import InputStreams
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.current_step import CurrentStep
from taskmates.core.workflows.states.interrupted import Interrupted
from taskmates.core.workflows.states.interrupted_or_killed import InterruptedOrKilled
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.core.workflows.states.return_value import ReturnValue
from taskmates.lib.not_set.not_set import NOT_SET
from taskmates.logging import logger, file_logger
from taskmates.types import Chat


# class CompletionRunEnvironment(TypedDict):
#     current_step: int
#     max_steps: int
#
#
# class MarkdownCompleteState(TypedDict):
#     interrupted: Interrupted
#     interrupted_or_killed: InterruptedOrKilled
#     return_value: ReturnValue
#     markdown_chat: MarkdownChat
#     current_step: CurrentStep
#     max_steps_check: MaxStepsCheck


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

        await self.start_workflow(markdown_chat, parent_signals,
                                  markdown_completion=current_run.signals["markdown_completion"])

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
                ]),
            ):
                should_continue = await self.complete_section(markdown_chat,
                                                              step_run.state,
                                                              step_run.signals)

                await self.end_section(state["markdown_chat"].get()["full"], step_run.signals["markdown_completion"])

                markdown_chat = state["markdown_chat"].get()["full"]

                if not should_continue:
                    break

        await self.end_workflow(
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

        await next_completion.perform_completion(chat,
                                                 completion_signals["control"],
                                                 completion_signals["markdown_completion"],
                                                 completion_signals["status"])

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

        # Merge the parsed run_opts from markdown front matter into the runtime context
        # This allows model and other configurations from the front matter to take effect
        if chat.get("run_opts"):
            run.context["run_opts"].update(chat["run_opts"])

        return chat

    async def end_section(self, markdown_chat: str, markdown_completion_signals: MarkdownCompletionSignals):
        await self._append_trailing_newlines(markdown_chat, markdown_completion_signals)

    async def start_workflow(self, markdown_chat,
                             parent_signals,
                             markdown_completion: MarkdownCompletionSignals,

                             ):
        await self._append_trailing_newlines(markdown_chat, parent_signals["markdown_completion"])

        prefixed_text = '\n'.join('> ' + line for line in markdown_chat.splitlines())

        prompt = "Consider the conversation: \n\n" + prefixed_text + \
                 ("\n\n"
                  "Classify the conversation above as one of: question|coding_task|feedback")

        # workflow = SdkCompletionRunner(run_opts=dict(model="claude-3-5-haiku-latest"))
        # result = await workflow.run(markdown_chat=prompt)

        # async def attempt_sdk_completion(context, markdown_chat):
        #     with Objective(key=ObjectiveKey(outcome="request_classification")).environment(context=context) as run:
        #         await run.signals["status"].start.send_async({})
        #         steps = {
        #             "markdown_complete": MarkdownComplete()
        #         }
        #
        #         return await steps["markdown_complete"].fulfill(**{"markdown_chat": markdown_chat})

        # result = await attempt_sdk_completion(self.context, prompt)

        # TODO
        # LlmCompletionProvider().perform_completion()
        # api_request()

        # await markdown_completion.formatting.send_async(f"[//]: # (start workflow: {result})\n\n")

    async def end_workflow(self,
                           markdown_chat: str,
                           context: RunContext,
                           markdown_completion: MarkdownCompletionSignals,
                           status: StatusSignals,
                           interrupted_or_killed: InterruptedOrKilled):
        chat = await self.get_markdown_chat(markdown_chat)

        if CompletionProvider.has_truncated_code_cell(chat):
            logger.debug("Truncated completion assistance")
            return

        # await markdown_completion.formatting.send_async("[//]: # (end workflow)\n\n")

        await self._append_next_responder(
            chat=chat,
            context=context,
            markdown_completion=markdown_completion,
            interrupted_or_killed=interrupted_or_killed
        )

        await status.success.send_async({})
        logger.debug("Finished completion assistance")

    async def _append_next_responder(self,
                                     chat: Chat,
                                     context: RunContext,
                                     markdown_completion: MarkdownCompletionSignals,
                                     interrupted_or_killed: InterruptedOrKilled):
        run = RUN.get()
        max_steps_reached = run.state["max_steps_check"].should_break()

        if context['runner_config']["interactive"] and not interrupted_or_killed.get() and not max_steps_reached:
            recipient = chat["messages"][-1]["recipient"]
            if recipient:
                await markdown_completion.next_responder.send_async(f"**{recipient}>** ")

    async def _append_trailing_newlines(self, markdown_chat: str, markdown_completion: MarkdownCompletionSignals):
        chat = await self.get_markdown_chat(markdown_chat)

        if CompletionProvider.has_truncated_code_cell(chat):
            return

        separator = compute_separator(markdown_chat)
        if separator:
            await markdown_completion.formatting.send_async(separator)


@pytest.mark.asyncio
async def test_markdown_front_matter_model_override(tmp_path):
    """Test that model specified in markdown front matter overrides the default model in runtime context"""
    from pathlib import Path
    from taskmates.defaults.context_defaults import ContextDefaults

    # Create a markdown with model in front matter
    markdown_with_model = """---
model: echo
---

Test message
"""

    # Set up the runtime context with default model
    context = ContextDefaults().build()
    initial_model = context["run_opts"]["model"]

    # Add required runner_environment and runner_config
    context["runner_environment"]["markdown_path"] = str(tmp_path / "test.md")
    context["runner_config"]["taskmates_dirs"] = [Path(__file__).parent.parent.parent.parent / "defaults"]

    # Create a run environment
    objective = Objective(key=ObjectiveKey(outcome="test_front_matter", inputs={}))
    run = Run(
        objective=objective,
        context=context,
        signals={},
        state={},
        daemons={}
    )

    with run:
        workflow = MarkdownComplete()

        # Get the parsed chat
        chat = await workflow.get_markdown_chat(markdown_with_model)

        # Verify the runtime context has been updated with the model from front matter
        assert RUN.get().context["run_opts"]["model"] == "echo"
        assert RUN.get().context["run_opts"]["model"] != initial_model


@pytest.mark.asyncio
async def test_no_recipient_prompt_when_max_steps_reached(tmp_path):
    """Test that recipient prompt is not appended when max_steps is reached"""
    from pathlib import Path
    from taskmates.defaults.context_defaults import ContextDefaults

    # Create a markdown chat with a recipient
    markdown_chat = """\
        ---
        participants:
          assistant:
            model: echo
        ---
        
        **user>** Hello
        
        **assistant>** Hi there!
        """

    # Set up the runtime context with max_steps = 1
    context = ContextDefaults().build()
    context["run_opts"]["max_steps"] = 1
    context["runner_config"]["interactive"] = True
    context["runner_environment"]["markdown_path"] = str(tmp_path / "test.md")
    context["runner_config"]["taskmates_dirs"] = [Path(__file__).parent.parent.parent.parent / "defaults"]

    # Create a list to capture signal emissions
    captured_signals = []

    # Create markdown completion signals with a custom handler
    markdown_completion_signals = MarkdownCompletionSignals()

    async def capture_next_responder(data):
        captured_signals.append(("next_responder", data))

    markdown_completion_signals.next_responder.connect(capture_next_responder)

    # Create a run environment
    objective = Objective(key=ObjectiveKey(outcome="test_max_steps", inputs={}))
    run = Run(
        objective=objective,
        context=context,
        signals={
            "control": ControlSignals(),
            "status": StatusSignals(),
            "markdown_completion": markdown_completion_signals,
        },
        state={
            "interrupted": Interrupted(),
            "interrupted_or_killed": InterruptedOrKilled(),
            "return_value": ReturnValue(),
            "markdown_chat": MarkdownChat(),
            "current_step": CurrentStep(),
            "max_steps_check": MaxStepsCheck(),
        },
        daemons={}
    )

    with run:
        workflow = MarkdownComplete()

        # Set current_step to exceed max_steps
        run.state["current_step"].set(2)  # This is > max_steps (1)

        # Get the parsed chat
        chat = await workflow.get_markdown_chat(markdown_chat)

        # Call _append_next_responder
        await workflow._append_next_responder(
            chat=chat,
            context=run.context,
            markdown_completion=markdown_completion_signals,
            interrupted_or_killed=run.state["interrupted_or_killed"]
        )

        # Verify that next_responder was NOT called because max_steps was reached
        assert len(captured_signals) == 0, "Expected no next_responder signal when max_steps is reached"

        # Now test that it DOES send when max_steps is not reached
        run.state["current_step"].set(1)  # This is <= max_steps (1)

        await workflow._append_next_responder(
            chat=chat,
            context=run.context,
            markdown_completion=markdown_completion_signals,
            interrupted_or_killed=run.state["interrupted_or_killed"]
        )

        # Verify that next_responder WAS called
        assert len(captured_signals) == 1, "Expected next_responder signal when max_steps is not reached"
        assert captured_signals[0] == ("next_responder", "**assistant>** ")
