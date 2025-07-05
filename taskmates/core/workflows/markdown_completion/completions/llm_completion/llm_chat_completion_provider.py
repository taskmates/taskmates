import pytest
from typeguard import typechecked

from taskmates.core.markdown_chat.metadata.get_model_client import get_model_client
from taskmates.core.markdown_chat.metadata.get_model_conf import get_model_conf
from taskmates.core.workflow_engine.run import RUN
from taskmates.core.workflows.markdown_completion.completions.completion_provider import CompletionProvider
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.llm_completion_request import LlmCompletionRequest
from taskmates.core.workflows.markdown_completion.completions.llm_completion.request.prepare_request_payload import \
    prepare_request_payload
from taskmates.core.workflows.markdown_completion.completions.llm_completion.response.llm_completion_markdown_appender import \
    LlmCompletionMarkdownAppender
from taskmates.core.workflows.signals.control_signals import ControlSignals
from taskmates.core.workflows.signals.llm_chat_completion_signals import LlmChatCompletionSignals
from taskmates.core.workflows.signals.markdown_completion_signals import MarkdownCompletionSignals
from taskmates.core.workflows.signals.status_signals import StatusSignals
from taskmates.types import Chat


@typechecked
class LlmChatCompletionProvider(CompletionProvider):
    def can_complete(self, chat):
        if self.has_truncated_code_cell(chat):
            return True

        last_message = chat["messages"][-1]
        recipient_role = last_message["recipient_role"]
        return recipient_role is not None and not recipient_role == "user"

    @typechecked
    async def perform_completion(
            self,
            chat: Chat,
            control_signals: ControlSignals,
            markdown_completion_signals: MarkdownCompletionSignals,
            status_signals: StatusSignals,
    ):
        contexts = RUN.get().context

        model_alias = contexts["run_opts"]["model"]

        taskmates_dirs = contexts["runner_config"]["taskmates_dirs"]

        model_conf = get_model_conf(model_alias=model_alias,
                                    messages=chat["messages"],
                                    taskmates_dirs=taskmates_dirs)
        model_conf.update({
            "temperature": 0.2,
            "stop": ["\n######"],
        })

        model_conf["stop"].extend(self.get_usernames_stop_sequences(chat))

        client = get_model_client(model_spec=model_conf)

        request_payload = prepare_request_payload(chat, model_conf)

        # Create the request
        request = LlmCompletionRequest(client, request_payload)

        markdown_appender = LlmCompletionMarkdownAppender(
            recipient=chat["messages"][-1]["recipient"],
            last_tool_call_id=self.get_last_tool_call_index(chat),
            is_resume_request=self.has_truncated_code_cell(chat),
            markdown_completion_signals=markdown_completion_signals
        )

        # Connect the markdown appender to the request's chunk signal
        request.on_chunk(markdown_appender.process_chat_completion_chunk)

        # Forward status signals
        request.forward_status_to(status_signals)

        # Forward control signals
        control_signals.interrupt.connect(request.control_signals.interrupt.send_async)
        control_signals.kill.connect(request.control_signals.kill.send_async)

        # Execute and return result
        return await request.execute()

    def get_last_tool_call_index(self, chat):
        last_tool_call_id = 0
        for m in chat['messages']:
            if m.get('tool_calls'):
                last_tool_call_id = int(m.get('tool_calls')[-1].get('id'))
        return last_tool_call_id

    def get_usernames_stop_sequences(self, chat):
        user_participants = ["user"]
        for name, config in chat["participants"].items():
            if config["role"] == "user" and name not in user_participants:
                user_participants.append(name)
        username_stop_sequences = [f"\n**{u}>** " for u in user_participants]
        return username_stop_sequences


@pytest.mark.asyncio
async def test_anthropic_tool_call_streaming_response(run):
    """Tests the full LLM completion pipeline with Anthropic tool call streaming fixture."""

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/anthropic_tool_call_streaming_response.jsonl"
        }
    }

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "What's the weather in San Francisco?",
        "run_opts": {}
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    result = await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

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
async def test_openai_tool_call_streaming_response(run):
    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "What's the weather in San Francisco?",
        "run_opts": {}
    }

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/openai_tool_call_streaming_response.jsonl"
        }
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_openai_get_weather_tool_call_streaming_response(run):
    """Tests with the production OpenAI get_weather fixture that's failing."""

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/openai_get_weather_tool_call_streaming_response.jsonl"
        }
    }

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "What's the weather in San Francisco?",
        "run_opts": {}
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    result = await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_openai_get_weather_tool_call_streaming_response_format_2(run):
    """Tests with the production OpenAI get_weather fixture format 2 with invalid_tool_calls."""

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/openai_get_weather_tool_call_streaming_response_format_2.jsonl"
        }
    }

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "What's the weather in San Francisco?",
        "run_opts": {}
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    result = await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\":\"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_gemini_streaming_response(run):
    """Tests the full LLM completion pipeline with Gemini streaming fixture."""

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/gemini_streaming_response.jsonl"
        }
    }

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "Count from 1 to 5", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "Count from 1 to 5",
        "run_opts": {}
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    result = await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = "1\n2\n3\n4\n5"

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"


@pytest.mark.asyncio
async def test_gemini_tool_call_streaming_response(run):
    """Tests the full LLM completion pipeline with Gemini tool call streaming fixture."""

    contexts = RUN.get().context
    contexts["run_opts"]["model"] = {
        "name": "fixture",
        "kwargs": {
            "fixture_path": "tests/fixtures/api-responses/gemini_tool_call_streaming_response.jsonl"
        }
    }

    # Create a chat that will trigger a completion
    chat = {
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?", "recipient": "assistant",
             "recipient_role": "assistant"}
        ],
        "participants": {"assistant": {"role": "assistant"}},
        "available_tools": [],
        "markdown_chat": "What's the weather in San Francisco?",
        "run_opts": {}
    }

    # Create the provider
    provider = LlmChatCompletionProvider()

    # Capture markdown output
    markdown_outputs = []

    async def capture_markdown(text, **kwargs):
        markdown_outputs.append(text)

    run.signals["markdown_completion"] = MarkdownCompletionSignals()
    run.signals["markdown_completion"].response.connect(capture_markdown, weak=False)

    # Perform the completion
    result = await provider.perform_completion(
        chat=chat,
        control_signals=run.signals["control"],
        markdown_completion_signals=run.signals["markdown_completion"],
        status_signals=run.signals["status"]
    )

    # Verify the COMPLETE output
    full_output = "".join(markdown_outputs)

    # The EXACT expected output based on the fixture
    expected_output = (
        "\n\n###### Steps\n\n"
        "- Get Weather [1] `{\"location\": \"San Francisco\"}`\n\n"
    )

    assert full_output == expected_output, f"Expected:\n{repr(expected_output)}\n\nGot:\n{repr(full_output)}"
