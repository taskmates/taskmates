import asyncio
import textwrap
from typing import TypedDict

from typeguard import typechecked

from taskmates.core.markdown_chat.compute_trailing_newlines import compute_trailing_newlines
from taskmates.core.workflow_engine.transaction import Transaction, Objective, ObjectiveKey
from taskmates.core.workflows.daemons.interrupt_request_daemon import InterruptRequestDaemon
from taskmates.core.workflows.daemons.interrupted_or_killed_daemon import InterruptedOrKilledDaemon
from taskmates.core.workflows.daemons.markdown_chat_daemon import MarkdownChatDaemon
from taskmates.core.workflows.markdown_completion.build_chat_completion_request import build_chat_completion_request
from taskmates.core.workflows.markdown_completion.completion_step_transaction import CompletionStepTransaction
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.markdown_completion.max_steps_check import MaxStepsCheck
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.states.current_step import CurrentStep
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.defaults.settings import Settings
from taskmates.lib.contextlib_.stacked_contexts import ensure_async_context_manager
from taskmates.logging import logger
from taskmates.types import ChatCompletionRequest, RunOpts


@typechecked
class MarkdownCompletion(Transaction):
    class State(TypedDict):
        markdown_chat: MarkdownChat
        current_step: CurrentStep
        max_steps_check: MaxStepsCheck

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        markdown_chat = self.objective.key['inputs'].get('markdown_chat')
        if not markdown_chat:
            raise ValueError("markdown_chat must be provided in objective inputs")

        current_step = CurrentStep()

        self.state.update({
            "markdown_chat": MarkdownChat(),
            "current_step": current_step,
            # TODO: this shouldn't be a state
            "max_steps_check": MaxStepsCheck(current_step,
                                             self.context['run_opts']["max_steps"]),
        })

        self.async_context_managers = list(self.async_context_managers) + [

            ensure_async_context_manager(InterruptRequestDaemon(
                self.emits["control"],
                self.interrupt_state)),
            ensure_async_context_manager(InterruptedOrKilledDaemon(
                self.consumes["status"],
                self.interrupt_state)),

            # NOTE: MarkdownChatDaemon is the sink for the completion chunks
            ensure_async_context_manager(MarkdownChatDaemon(
                self.consumes["execution_environment"],
                self.state["markdown_chat"])),
        ]

        # TODO: move this out
        if markdown_chat:
            self.state["markdown_chat"].append_to_format("full", markdown_chat)

    async def fulfill(self) -> str:
        async with self.async_transaction_context():
            markdown_chat = self.state["markdown_chat"].get()["full"]
            logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

            await self.start_workflow(self.state["markdown_chat"].get()["full"],
                                      chat=self.current_chat(),
                                      execution_environment_signals=self.consumes[
                                          "execution_environment"])

            while True:
                self.state["current_step"].increment()

                if self._should_terminate():
                    break

                # Create and execute the child transaction
                completion_step_transaction = self.create_completion_step_transaction(
                    self.state["current_step"].current_step,
                    self.current_chat())

                async with completion_step_transaction.async_transaction_context():
                    should_continue = await completion_step_transaction.fulfill()

                    # Get the updated markdown and rebuild the chat payload for end_section

                    # TODO: this should be part of completion_step_transaction
                    await self.end_section(self.state["markdown_chat"].get()["full"],
                                           self.current_chat(),
                                           completion_step_transaction.execution_context.consumes[
                                               "execution_environment"])

                    # TODO: set the result of the transaction and let
                    # Exit loop if completion indicates we shouldn't continue self._should_terminate() handle the break
                    if not should_continue:
                        break

            # Build final chat payload for end_workflow
            await self.end_workflow(
                chat=self.current_chat(),
                execution_environment=self.consumes["execution_environment"]
            )

            logger.debug("Finished completion assistance")

            # TODO: here's where we format the response
            response_format = self.objective.result_format["format"]
            response = self.state["markdown_chat"].get()[response_format]
            return response

    def current_chat(self) -> ChatCompletionRequest:
        return build_chat_completion_request(
            self.state["markdown_chat"].get()["full"],
            self.objective.key.get('inputs', {}),
            markdown_path=self.context["runner_environment"]["markdown_path"],
            run_opts=self.context.get("run_opts", {})
        )

    def create_completion_step_transaction(self,
                                           step: int,
                                           chat_payload: ChatCompletionRequest,
                                           ):
        return self.create_child_transaction(
            outcome=f"{self.objective.key['outcome']}-step-{step}",
            inputs={"chat_payload": chat_payload},
            transaction_class=CompletionStepTransaction
        )

    async def end_section(self, markdown_chat: str, chat: ChatCompletionRequest,
                          execution_environment_signals: ExecutionEnvironmentSignals):
        await self._append_trailing_newlines(markdown_chat, chat, execution_environment_signals)

    async def start_workflow(self, markdown_chat, chat: ChatCompletionRequest,
                             execution_environment_signals: ExecutionEnvironmentSignals):
        await self._append_trailing_newlines(markdown_chat, chat, execution_environment_signals)

        # prefixed_text = '\n'.join('> ' + line for line in markdown_chat.splitlines())
        #
        # prompt = "Consider the conversation: \n\n" + prefixed_text + \
        #          ("\n\n"
        #           "Classify the conversation above as one of: question|coding_task|feedback")
        #
        # request_classification = self.create_child_transaction(
        #     outcome="request_classification",
        #     inputs={"markdown_chat": prompt},
        #     transaction_class=MarkdownCompletion
        # )
        #
        # result = await request_classification.fulfill()
        #
        #
        # await execution_environment.response.send_async(sender="formatting", value=f"[//]: # (start workflow: {result})\n\n")

    async def end_workflow(self,
                           chat: ChatCompletionRequest,
                           execution_environment: ExecutionEnvironmentSignals):
        if has_truncated_code_cell(chat) or self._should_terminate():
            return

        # await execution_environment.response.send_async(sender="formatting", value="[//]: # (end workflow)\n\n")

        # TODO: here's where we also format the response
        if self.objective.result_format["interactive"]:
            await self._append_next_responder(
                chat=chat,
                execution_environment=execution_environment
            )

    async def _append_next_responder(self,
                                     chat: ChatCompletionRequest,
                                     execution_environment: ExecutionEnvironmentSignals):

        recipient = chat["messages"][-1]["recipient"]
        if not recipient:
            return
        await execution_environment.response.send_async(sender="next_responder", value=f"**{recipient}>** ")

    async def _append_trailing_newlines(self, markdown_chat: str, chat: ChatCompletionRequest,
                                        execution_environment: ExecutionEnvironmentSignals):
        if has_truncated_code_cell(chat):
            return

        newlines = compute_trailing_newlines(markdown_chat)
        if newlines:
            await execution_environment.response.send_async(sender="formatting", value=newlines)

    def _should_terminate(self) -> bool:
        if self.state["max_steps_check"].should_break():
            return True
        if self.should_terminate():
            logger.debug(
                f"Transaction terminated: future_done={self.result_future.done()}, interrupt_state={self.interrupt_state}")
            return True
        return False

    @staticmethod
    def complete(markdown_chat: str,
                 run_opts: RunOpts = None):

        # TODO: pass @subject
        # TODO: pass annotators

        context = Settings().get()
        context["run_opts"].update(run_opts or {})

        instance = MarkdownCompletion(
            objective=Objective(key=ObjectiveKey(
                outcome=MarkdownCompletion.__name__,
                inputs={"markdown_chat": markdown_chat}
            )),
            context=context
        )

        result = asyncio.run(instance.fulfill())
        return result


async def test_completion_result(tmp_path):
    markdown_chat = "**user>** Hello\n\n"

    # Execute completion
    result = await MarkdownCompletion.create({"markdown_chat": markdown_chat}).fulfill()

    expected_result = textwrap.dedent("""\
    **assistant>** 
    > Hello
    > 
    > 
    
    """)

    # Verify the result contains the expected quoted response
    assert result == expected_result


async def test_completion_streaming(tmp_path):
    # Create MarkdownCompletion transaction
    markdown_chat = "**user>** Hello\n\n"

    markdown_completion = MarkdownCompletion.create(inputs={"markdown_chat": markdown_chat})

    # Track response chunks
    response_chunks = []

    async def capture_response(sender, value):
        response_chunks.append(value)

    # Connect signal handler
    markdown_completion.consumes["execution_environment"].response.connect(capture_response)

    # Execute completion
    await markdown_completion.fulfill()

    expected_result = textwrap.dedent("""\
    **assistant>** 
    > Hello
    > 
    > 
    
    """)

    # Verify response was captured through signals
    full_response = "".join(response_chunks)
    assert full_response == expected_result

# TODO: add test for format ?
