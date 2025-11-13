import pytest
from typeguard import typechecked

from taskmates.core.workflow_engine.base_signals import connected_signals
from taskmates.core.workflow_engine.transaction_manager import runtime
from taskmates.core.workflow_engine.transactions.transaction import Transaction
from taskmates.core.workflow_engine.transactions.transactional import transactional
from taskmates.core.workflows.markdown_completion.completions.has_truncated_code_cell import has_truncated_code_cell
from taskmates.core.workflows.markdown_completion.completions.llm_completion._get_last_tool_call_index import \
    _get_last_tool_call_index
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.llm_completion_request import \
    LlmCompletionRequest
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_markdown_appender import \
    LlmCompletionMarkdownAppender
from taskmates.core.workflows.markdown_completion.completions.section_completion import SectionCompletion
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.execution_environment_signals import ExecutionEnvironmentSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.core.workflows.states.markdown_chat import MarkdownChat
from taskmates.runtimes.cli.collect_markdown_bindings import CollectMarkdownBindings
from taskmates.types import CompletionRequest


@typechecked
class LlmChatSectionCompletion(SectionCompletion):
    def can_complete(self, chat: CompletionRequest):
        messages = chat["messages"]

        if has_truncated_code_cell(messages[-1]):
            return True

        last_message = messages[-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @transactional
    async def perform_completion(self, chat: CompletionRequest) -> str:
        markdown_chat_state = MarkdownChat()

        async with CollectMarkdownBindings(runtime.transaction, markdown_chat_state):
            control_signals: ControlSignals = runtime.transaction.emits["control"]
            execution_environment_signals: ExecutionEnvironmentSignals = runtime.transaction.consumes[
                "execution_environment"]
            status_signals: StatusSignals = runtime.transaction.consumes["status"]

            messages = chat["messages"]
            request = LlmCompletionRequest(chat)

            markdown_appender = LlmCompletionMarkdownAppender(
                recipient=messages[-1]["recipient"],
                last_tool_call_id=_get_last_tool_call_index(chat),
                is_resume_request=has_truncated_code_cell(messages[-1]),
                execution_environment_signals=execution_environment_signals
            )

            # Forward status signals
            with request.llm_chat_completion_signals.llm_chat_completion.connected_to(
                    markdown_appender.process_chat_completion_chunk), \
                    connected_signals([
                        (request.status_signals, status_signals),
                        (control_signals, request.control_signals),

                    ]):
                # Execute streaming since we have a receiver connected (markdown_appender)
                await request.execute_streaming()

        return markdown_chat_state.get()["completion"]


@pytest.mark.asyncio
async def test_anthropic_tool_call_streaming_response(transaction: Transaction):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/anthropic_tool_call_streaming_response.jsonl"
                }
            }
        }
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        result = await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "I'll check the current weather in San Francisco for you."
        "\n\n###### Steps\n\n"
        "- Get Weather [2] `{\"location\": \"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_openai_tool_call_streaming_response(transaction: Transaction):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_tool_call_streaming_response.jsonl"
                }
            }
        }
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_openai_get_weather_tool_call_streaming_response(transaction: Transaction):
    """Tests with the production OpenAI get_weather fixture that's failing."""

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_get_weather_tool_call_streaming_response.jsonl"
                }
            }}
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        result = await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_openai_get_weather_tool_call_streaming_response_format_2(transaction: Transaction):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/openai_get_weather_tool_call_streaming_response_format_2.jsonl"
                }
            }
        }
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        result = await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_gemini_streaming_response(transaction: Transaction):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "Count from 1 to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/gemini_streaming_response.jsonl"
                }
            }
        }
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        result = await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = "1\n2\n3\n4\n5"

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_gemini_tool_call_streaming_response(transaction: Transaction):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "run_opts": {
            "model": {
                "name": "fixture",
                "kwargs": {
                    "fixture_path": "tests/fixtures/api-responses/gemini_tool_call_streaming_response.jsonl"
                }
            }
        }
    }

    # Create the provider
    provider = LlmChatSectionCompletion()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(sender, value):
        markdown_outputs.append(value)

    execution_environment_signals = ExecutionEnvironmentSignals(name="ExecutionEnvironmentSignals")
    control_signals = ControlSignals(name="ControlSignals")
    status_signals = StatusSignals(name="StatusSignals")

    execution_environment_signals.response.connect(capture_markdown, sender="response", weak=False)

    # Set up signals on transaction
    transaction.emits["control"] = control_signals
    transaction.consumes["execution_environment"] = execution_environment_signals
    transaction.consumes["status"] = status_signals

    # Perform the completion
    async with transaction.async_transaction_context():
        result = await provider.perform_completion(chat=chat)

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\": \"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"
