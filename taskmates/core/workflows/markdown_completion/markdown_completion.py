import textwrap

from typeguard import typechecked

from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflows.markdown_completion.append_trailing_newlines import append_trailing_newlines
from taskmates.core.workflows.markdown_completion.build_completion_request import build_completion_request
from taskmates.core.workflows.markdown_completion.compute_next_completion import compute_next_completion
from taskmates.core.workflows.markdown_completion.interrupt_signals_bindings import InterruptSignalsBindings
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.states.current_step import CurrentStep
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.logging import logger, file_logger
from taskmates.runtimes.cli.collect_markdown_bindings import CollectMarkdownBindings
from taskmates.types import CompletionRequest


@typechecked
class MarkdownCompletion:
    def __init__(self):
        self.current_step: CurrentStep = CurrentStep()

    @transactional()
    async def fulfill(self, markdown_chat: str) -> str:
        transaction = runtime.transaction
        logger.debug(f"Starting MarkdownComplete with markdown:\n{markdown_chat}")

        # TODO: merge MarkdownChat and CompletionPayload
        # 1. make current_chat / build_completion_request incremental - parse only the the additional markdown
        markdown_chat_state = MarkdownChat(initial=markdown_chat)

        async with InterruptSignalsBindings(transaction, transaction.interrupt_state), \
                CollectMarkdownBindings(transaction, markdown_chat_state):
            self.current_step.set(1)

            await self.before_start_completion(
                message=self.current_chat(markdown_chat_state)["messages"][-1],
                execution_environment_signals=transaction.consumes["execution_environment"])

            while True:
                chat = self.current_chat(markdown_chat_state)
                file_logger.debug("parsed_chat.json", content=chat)

                # TODO: if recipient == "user", set transaction result

                max_steps = runtime.transaction.context['run_opts']["max_steps"] if runtime.transaction else 10000
                if self.current_step.get() > max_steps:
                    transaction.interrupt_state.value = "interrupted"

                # Break if interrupted or killed
                if transaction.interrupt_state.is_terminated():
                    break

                # Execute the section completion
                completion_assistance = compute_next_completion(chat)

                if not completion_assistance:
                    # TODO: set the result of the transaction instead
                    break

                await completion_assistance.perform_completion(chat=chat)
                # TODO: this should be part of completion_step_transaction
                await self.end_section(self.current_chat(markdown_chat_state)["messages"][-1],
                                       transaction.consumes["execution_environment"])

                self.current_step.increment()

            if not transaction.interrupt_state.is_terminated():
                # Build final chat payload for end_workflow
                chat = self.current_chat(markdown_chat_state)
                await self.after_finish_completion(
                    chat=chat,
                    execution_environment=transaction.consumes["execution_environment"]
                )

            logger.debug("Finished completion assistance")

            # TODO: here's where we format the response
            response_format = transaction.objective.result_format["format"]
            response = markdown_chat_state.get()[response_format]
            return response

    def current_chat(self, markdown_chat_state: MarkdownChat) -> CompletionRequest:
        transaction = runtime.transaction
        run_opts = transaction.context.get("run_opts", {}).copy()
        run_opts["inputs"] = {**run_opts.get("inputs", {}), **transaction.objective.key.get('inputs', {})}
        return build_completion_request(
            markdown_chat=markdown_chat_state.get()["full"],
            markdown_path=transaction.context["runner_environment"]["markdown_path"],
            run_opts=run_opts
        )

    async def end_section(self, message: dict,
                          execution_environment_signals: ExecutionEnvironmentSignals):
        await append_trailing_newlines(message, execution_environment_signals)

    async def before_start_completion(self, message: dict,
                                      execution_environment_signals: ExecutionEnvironmentSignals):
        await append_trailing_newlines(message, execution_environment_signals)

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

    async def after_finish_completion(self,
                                      chat: CompletionRequest,
                                      execution_environment: ExecutionEnvironmentSignals):
        transaction = runtime.transaction

        recipient = chat["messages"][-1]["recipient"]

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
