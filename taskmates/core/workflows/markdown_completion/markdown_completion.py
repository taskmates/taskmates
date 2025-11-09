import textwrap

from typeguard import typechecked

from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflows.markdown_completion.append_trailing_newlines import append_trailing_newlines
from taskmates.core.workflows.markdown_completion.build_completion_request import build_completion_request
from taskmates.core.workflows.markdown_completion.completion_section import CompletionSection
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.markdown_completion.interrupt_signals_bindings import InterruptSignalsBindings
from taskmates.core.workflows.markdown_completion.markdown_completion_state import MarkdownCompletionState
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.logging import logger
from taskmates.runtimes.cli.collect_markdown_bindings import CollectMarkdownBindings
from taskmates.types import CompletionRequest


@typechecked
class MarkdownCompletion:
    @transactional()
    async def fulfill(self, markdown_chat: str) -> str:
        transaction = runtime.transaction

        # Initialize state from transaction
        state: MarkdownCompletionState = MarkdownCompletionState(
            inputs={"markdown_chat": markdown_chat},
            max_steps=transaction.context['run_opts']["max_steps"]
        )
        async with InterruptSignalsBindings(transaction, transaction.interrupt_state), \
                CollectMarkdownBindings(transaction, state.state['markdown_chat']):
            markdown_chat = state.state["markdown_chat"].get()["full"]
            logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

            await self.start_workflow(state.state["markdown_chat"].get()["full"],
                                      messages=self.current_chat(state)["messages"],
                                      execution_environment_signals=transaction.consumes[
                                          "execution_environment"])

            while True:
                state.state["current_step"].increment()

                if self._should_terminate(state):
                    break

                # Create and execute the child transaction
                child_transaction = self.create_completion_step_transaction(
                    state.state["current_step"].current_step,
                    self.current_chat(state))

                workflow = CompletionSection()

                async with child_transaction.async_transaction_context():
                    should_continue = await workflow.fulfill(child_transaction)

                    # Get the updated markdown and rebuild the chat payload for end_section

                    # TODO: this should be part of completion_step_transaction
                    await self.end_section(state.state["markdown_chat"].get()["full"],
                                           self.current_chat(state)["messages"],
                                           child_transaction.consumes[
                                               "execution_environment"])

                    # TODO: set the result of the transaction and let
                    # Exit loop if completion indicates we shouldn't continue self._should_terminate() handle the break
                    if not should_continue:
                        break

            # Build final chat payload for end_workflow
            chat = self.current_chat(state)
            await self.end_workflow(
                state=state,
                messages=chat["messages"],
                recipient=chat["messages"][-1]["recipient"],
                execution_environment=transaction.consumes["execution_environment"]
            )

            logger.debug("Finished completion assistance")

            # TODO: here's where we format the response
            response_format = transaction.objective.result_format["format"]
            response = state.state["markdown_chat"].get()[response_format]
            return response

    def current_chat(self, state: MarkdownCompletionState) -> CompletionRequest:
        transaction = runtime.transaction
        return build_completion_request(
            state.state["markdown_chat"].get()["full"],
            transaction.objective.key.get('inputs', {}),
            markdown_path=transaction.context["runner_environment"]["markdown_path"],
            run_opts=transaction.context.get("run_opts", {})
        )

    def create_completion_step_transaction(self,
                                           step: int,
                                           chat_payload: CompletionRequest,
                                           ):
        transaction = runtime.transaction
        return transaction.create_child_transaction(
            outcome=f"{transaction.objective.key['outcome']}-step-{step}",
            inputs={"chat_payload": chat_payload}
        )

    async def end_section(self, markdown_chat: str, messages: list[dict],
                          execution_environment_signals: ExecutionEnvironmentSignals):
        await append_trailing_newlines(markdown_chat, messages, execution_environment_signals)

    async def start_workflow(self, markdown_chat, messages: list[dict],
                             execution_environment_signals: ExecutionEnvironmentSignals):
        await append_trailing_newlines(markdown_chat, messages, execution_environment_signals)

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
                           state: MarkdownCompletionState,
                           messages: list[dict],
                           recipient: str | None,
                           execution_environment: ExecutionEnvironmentSignals):
        transaction = runtime.transaction

        if has_truncated_code_cell(messages) or self._should_terminate(state):
            return

        # await execution_environment.response.send_async(sender="formatting", value="[//]: # (end workflow)\n\n")

        # TODO: here's where we also format the response
        if transaction.objective.result_format["interactive"]:
            await self._append_next_responder(
                recipient=recipient,
                execution_environment=execution_environment
            )

    async def _append_next_responder(self,
                                     recipient: str | None,
                                     execution_environment: ExecutionEnvironmentSignals):
        if not recipient:
            return
        await execution_environment.response.send_async(sender="next_responder", value=f"**{recipient}>** ")

    def _should_terminate(self, state: MarkdownCompletionState) -> bool:
        transaction = runtime.transaction
        if state.state["max_steps_check"].should_break():
            return True
        if transaction.is_terminated():
            logger.debug(
                f"Transaction terminated: future_done={transaction.result_future.done()}, interrupt_state={transaction.interrupt_state}")
            return True
        return False


async def test_completion_result(tmp_path):
    markdown_chat = "**user>** Hello\n\n"

    # Execute completion
    workflow = MarkdownCompletion()
    result = await workflow.fulfill(markdown_chat=markdown_chat)

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

    # Use a temporary cache directory for this test
    from taskmates.core.workflow_engine.transaction_manager import TransactionManager, runtime
    test_manager = TransactionManager(cache_dir=str(tmp_path / "cache"))

    with runtime.transaction_manager_context(test_manager):
        workflow = MarkdownCompletion()
        transaction = test_manager.build_executable_transaction(
            operation=workflow.fulfill.operation,
            outcome=workflow.fulfill.outcome,
            inputs={"markdown_chat": markdown_chat},
            workflow_instance=workflow
        )

        # Track response chunks
        response_chunks = []

        async def capture_response(sender, value):
            response_chunks.append(value)

        # Connect signal handler before starting the workflow
        transaction.consumes["execution_environment"].response.connect(capture_response)

        # Execute the transaction
        result = await transaction()

        expected_result = textwrap.dedent("""\
        **assistant>** 
        > Hello
        > 
        > 
        
        """)

        # Verify response was captured through signals
        full_response = "".join(response_chunks)
        assert full_response == expected_result
        assert result == expected_result

# TODO: add test for format ?
